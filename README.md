# Dirty Version

I threw this together as a proof of concept about how we can simplify our versioning scheme in the [ASU Repository](http://repository.asu.edu).

It only requires that your versioned model subclass [**versions.models.Versionable**](versions/models.py). It uses a custom manager for querying easy access to current versions or historical versions. 




