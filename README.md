# Dirty Version

I threw this together as a proof of concept about how we can simplify our versioning scheme in the [ASU Repository](http://repository.asu.edu).

This is based on [tuple versioning](http://en.wikipedia.org/wiki/Tuple-versioning) of a [type 2 slowly changing dimension] (http://en.wikipedia.org/wiki/Slowly_changing_dimension#Type_2).

Versioning a model requires only that you subclass [**versions.models.Versionable**](https://github.com/cordmata/dirtyversion/blob/master/versions/models.py). The model will have a custom default manager to provide access to current or historical versions.

If a versioned resource is related to another versioned resource (currently only tested for foreign key relationships) the [**versions.models.VersionedRelation**](https://github.com/cordmata/dirtyversion/blob/master/versions/models.py) class is provided as a surrogate for reverse attribute lookup as provided by Django. This ensures that you are dealing with the appropriate versions of the related resources. Hooking this up is a bit awkward, but this *is* just a POC.  

## Try it out!

Usage is described in detail in the [unit tests](https://github.com/cordmata/dirtyversion/blob/master/versions/tests.py). Everything should be set up to run the tests out of the box -- just clone the repo and run:

    ./manage.py syncdb
    ./manage.py test versions

