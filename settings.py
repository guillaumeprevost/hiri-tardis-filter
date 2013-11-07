from settings_changeme import *

DEBUG = True

#Post Save Filters
POST_SAVE_FILTERS = [
     ("tardis.tardis_portal.filters.flexstation.make_filter",
     ["FLEXSTATION", "http://rmit.edu.au/flexstation"]), # Flexstation III filter
]

MIDDLEWARE_CLASSES += ('tardis.tardis_portal.filters.FilterInitMiddleware',) # enables the filters middleware class
