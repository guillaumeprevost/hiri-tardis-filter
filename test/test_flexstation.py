from os import path
from compare import expect, ensure

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client

from tardis.tardis_portal.filters.flexstation import FlexstationFilter
from tardis.tardis_portal.models import User, UserProfile, \
    ObjectACL, Experiment, Dataset, Dataset_File, Replica, Location
from tardis.tardis_portal.models.parameters import DatasetParameterSet
from tardis.tardis_portal.ParameterSetManager import ParameterSetManager

from tardis.tardis_portal.tests.test_download import get_size_and_sha512sum


class FlexstationFilterTestCase(TestCase):

    TEST_FILES_PATH =   ('050511V1 Pmutants rep1.pda',
                         '050511V1 Pmutants rep2.pda',
                         '050511V1 Pmutants rep3.pda',
                         '061412 BIM1 and 2APBlatin square.pda',
                         '230511 V1 Pmuants rep1.pda',
                         'BGD131010 3759 and 3720.pda',
                         'BGD131010 3833 and 3971.pda',
    )

    def setUp(self):
        # Create test owner without enough details
        username, email, password = ('testuser',
                                     'testuser@example.test',
                                     'password')
        user = User.objects.create_user(username, email, password)
        profile = UserProfile(user=user, isDjangoAccount=True)
        profile.save()

        Location.force_initialize()

        # Create test experiment and make user the owner of it
        experiment = Experiment(title='Text Experiment',
                                institution_name='Test Uni',
                                created_by=user)
        experiment.save()
        acl = ObjectACL(
            pluginId='django_user',
            entityId=str(user.id),
            content_object=experiment,
            canRead=True,
            isOwner=True,
            aclOwnershipType=ObjectACL.OWNER_OWNED,
        )
        acl.save()

        dataset = Dataset(description='dataset description...')
        dataset.save()
        dataset.experiments.add(experiment)
        dataset.save()

        def create_datafile(file_path):
            testfile = path.join(path.dirname(__file__), 'fixtures', file_path)

            size, sha512sum = get_size_and_sha512sum(testfile)

            datafile = Dataset_File(dataset=dataset,
                                    filename=path.basename(testfile),
                                    size=size,
                                    sha512sum=sha512sum)
            datafile.save()
            base_url = 'file://' + path.abspath(path.dirname(testfile))
            location = Location.load_location({
                'name': 'test-flexstation', 'url': base_url, 'type': 'external',
                'priority': 10, 'transfer_provider': 'local'})
            replica = Replica(datafile=datafile,
                              url='file://'+ path.abspath(testfile),
                              protocol='file',
                              location=location)
            replica.verify()
            replica.save()
            return Dataset_File.objects.get(pk=datafile.pk)

        self.dataset = dataset
        self.datafiles = [create_datafile(self.TEST_FILES_PATH[i]) for i in (0,1,2,3,4,5,6)]


    def testFlexstationSimple(self):
        """
        Simple test running the filter and making sure the Softmax version number was saved
        """
        filter = FlexstationFilter("Flexstation Test Schema", "http://rmit.edu.au/flexstation_test")
        filter.__call__(None, instance=self.datafiles[0])
        # Check a parameter set was created for the datafile
        datafile = Dataset_File.objects.get(id=self.datafiles[0].id)
        expect(datafile.getParameterSets().count()).to_equal(1)

         # Check that at least the verion number was extracted
        psm = ParameterSetManager(datafile.getParameterSets()[0])
        expect(psm.get_param('softmax_version', True)).to_equal('5.42.1.0')

        # Check we won't create a duplicate datafile
        filter = FlexstationFilter("Flexstation Test Schema", "http://rmit.edu.au/flexstation_test")
        filter.__call__(None, instance=self.datafiles[0])
        datafile = Dataset_File.objects.get(id=self.datafiles[0].id)
        expect(datafile.getParameterSets().count()).to_equal(1)


    def testFlexstationAllFields(self):
        """
        Simple test running the filter and making sure the Softmax version number was saved
        """
        filter = FlexstationFilter("Flexstation Test Schema", "http://rmit.edu.au/flexstation_test")
        filter.__call__(None, instance=self.datafiles[0])
        # Check a parameter set was created for the datafile
        datafile = Dataset_File.objects.get(id=self.datafiles[0].id)
        expect(datafile.getParameterSets().count()).to_equal(1)

        # Check all the expected parameters are there
        psm = ParameterSetManager(datafile.getParameterSets()[0])
        expect(psm.get_param('softmax_version', True)).to_equal('5.42.1.0')
        expect(psm.get_param('experiment_name', True)).to_equal('Experiment#1')
        expect(psm.get_param('analysis_notes', True)).to_equal(u'Notes#1: TRPV1 Phosphate mutants\rCells seeded 48hrs prior 40K cel/well \rInduced with tetracycline for 3 hrs washed once with hepes (50microL/well) then loaded with fura2 for 1 hr (50 microL/well). then washed twice with 60microl or HEPES buffer per well finaly loaded with 60microl of hepes.\rCells:\rcolumn 1: Nt, 2: WtV1, 3: C1, 4: C2, 5: C3, 6: C4, 7: C5,  8: N1, 9: N6\rinjection 1: rows A-D buffer only, E-H 100microM SLIGRL\rinjection 2: Row A,E DMSO 1%, B,F 1microM CAPS, C,G 10microM CAPS, D,H 100microM caps')
        expect(psm.get_param('instrument_info', True)).to_equal('Flexstation III ROM v2.1.35 20May09')
        #expect(psm.get_param('plate_read_time', True)).to_equal('')
        #expect(psm.get_param('read_type', True)).to_equal('')
        #expect(psm.get_param('data_mode', True)).to_equal('')
        #expect(psm.get_param('data_type', True)).to_equal('')
        expect(psm.get_param('strips', True)).to_equal('1-9')
        expect(psm.get_param('trans1', True)).to_equal(u'H=80\xb5, R=4, V=20.0\xb5, \x4015')
        expect(psm.get_param('trans2', True)).to_equal(u'H=100\xb5, R=4, V=20.0\xb5, \x40115')
        expect(psm.get_param('kinetic_points', True)).to_equal(65.0)
        expect(psm.get_param('kinetic_flex_read_time', True)).to_equal(250.0)
        expect(psm.get_param('kinetic_flex_interval', True)).to_equal(3.9)
        #expect(psm.get_param('number_of_wavelengths', True)).to_equal('')
        expect(psm.get_param('read_wavelength', True)).to_equal('520 520')
        expect(psm.get_param('number_of_wells_or_cuvette', True)).to_equal(96.0)
        expect(psm.get_param('excitation_wavelengths', True)).to_equal('340 380')
        #expect(psm.get_param('read_per_well', True)).to_equal('')
        #expect(psm.get_param('pmt_settings', True)).to_equal('')

    def testFlexstationTwoExperimentsInFile(self):
        """
        Simple test running the filter and making sure the Softmax version number was saved
        """
        filter = FlexstationFilter("Flexstation Test Schema", "http://rmit.edu.au/flexstation_test")
        filter.__call__(None, instance=self.datafiles[5])
        # Check a parameter set was created for the datafile
        datafile = Dataset_File.objects.get(id=self.datafiles[5].id)
        expect(datafile.getParameterSets().count()).to_equal(1)

        # Check all the expected parameters are there
        psm = ParameterSetManager(datafile.getParameterSets()[0])
        expect(psm.get_param('softmax_version', True)).to_equal('5.4.52.1.0')
        expect(psm.get_param('experiment_name', True)).to_equal('Exp01')
        expect(psm.get_param('analysis_notes', True)).to_equal(
            u'Revision_101: PROTOCOL REVISION HISTORY:\rv1.0.0: original protocol created (MDC)\rv1.0.1: 06/30/05 - Updated, spell checked, & formatted to new style guide. (DW)\r\rREADER SUITABILITY:\r\nEMax, VMax, ThermoMax, VersaMax, SpectraMax, SpectraMax Plus, SpectraMax Plus 384, SpectraMax 190, SpectraMax 340PC, SpectraMax 340PC 384, SpectraMax M2, SpectraMax M5. Intro: MIPS resupply 3759, 3720  latin square\rcells seeded 48hrs prior using FTA. Cells were 95-100% confluent on the day of the experiment.\rColumns 1,3,5,7,9,11 are non-transfected HEK cells, columns 2,4,6,8,10,12 are hTRPV4 HEK.\rCells were induced the evening prior to assay with 0.1\xb5g/ml tet \rLoaded with FURA-2 at 805 Inhibitor at 900\rLatin square\r      1     2     3     4     5     6     \ra     x     x     x     x     x     x\rb     c    z     y      x     w    v    \rc     v     c     z     y     x     w\rd     w    v     c     z     y     x\re     x     w     v     c     z     y\rf      y     x     w     v     c     z\rg     z     y     x     w     v     c\rh     x     x     x     x     x     x\rc control V vehicle 0.1% DMSO, w 3759 10\xb5M x 3759 1\xb5M y 3720 10\xb5M z 3720 1\xb5M\rInjection 1 at 15"\rSLIGRL 30\xb5M\rInjection 2 at 80" \rGSK 30nM ')
        expect(psm.get_param('instrument_info', True)).to_equal('Flexstation III ROM v3.0.22 16Feb11')
        #expect(psm.get_param('plate_read_time', True)).to_equal('')
        #expect(psm.get_param('read_type', True)).to_equal('')
        #expect(psm.get_param('data_mode', True)).to_equal('')
        #expect(psm.get_param('data_type', True)).to_equal('')
        expect(psm.get_param('strips', True)).to_equal('1-12')
        expect(psm.get_param('trans1', True)).to_equal(u'H=80\xb5, R=4, V=20.0\xb5, \x4015')
        expect(psm.get_param('trans2', True)).to_equal(u'H=100\xb5, R=4, V=25.0\xb5, \x4080')
        expect(psm.get_param('kinetic_points', True)).to_equal(39.0)
        expect(psm.get_param('kinetic_flex_read_time', True)).to_equal(150.0)
        expect(psm.get_param('kinetic_flex_interval', True)).to_equal(3.9)
        #expect(psm.get_param('number_of_wavelengths', True)).to_equal('')
        expect(psm.get_param('read_wavelength', True)).to_equal('520 520')
        expect(psm.get_param('number_of_wells_or_cuvette', True)).to_equal(96.0)
        expect(psm.get_param('excitation_wavelengths', True)).to_equal('340 380')
        #expect(psm.get_param('read_per_well', True)).to_equal('')
        #expect(psm.get_param('pmt_settings', True)).to_equal('')
