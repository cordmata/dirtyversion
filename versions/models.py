import copy
import datetime
import uuid

from django.db import models

class VersionManager(models.Manager):
    
    use_for_related_fields = True 
    
    @property
    def current(self):
        return super(VersionManager, self).filter(clone_date__isnull=True)
    
    @property
    def history(self):
        return super(VersionManager, self).exclude(clone_date__isnull=True)\
                .order_by('-version_date')
    
    def create(self, **kwargs):
        ident = unicode(uuid.uuid4())
        now = datetime.datetime.now()
        kwargs['vid'] = ident
        kwargs['identity'] = ident
        kwargs['version_date'] = now
        kwargs['created_date'] = now
        return super(VersionManager, self).create(**kwargs)
        

class VersionedRelation(object):
    '''This works for ForeignKey relationships but I'm sure there are all sorts 
    of issues I'm ignoring for other relationship types.'''
    
    def __init__(self, model_class, attr):
        self.model_class = model_class
        self.attr = attr

    def __get__(self, instance, owner):
        filter_args = { self.attr: instance.identity }

        if not instance.clone_date:
            # if this is the head revision of the requesting model 
            # just return the heads of the relation
            return self.model_class.objects.current.filter(**filter_args)
            print '\n\n'
            print 'no clone date on {}'.format(instance.identity)
            print '\n\n'
        else:
            # If the requesting model is a revision, only get the
            # related revisions as of the time the version was cloned.
            #
            # This requires 2 queries, but it shouldn't be that bad.
            #
            # First, we find the latest version dates of the identities
            # which have a version_date previous to the clone_date of the 
            # requesting instance.
            instance_qs = self.model_class.objects.filter(**filter_args)
            latest_idents = instance_qs\
                            .filter(version_date__lt=instance.clone_date)\
                            .values('identity')\
                            .annotate(version_date=models.Max('version_date'))
            if not latest_idents:
                return instance_qs.none()
            # Here, latest_idents is a list of dicts indicating
            # the greatest version date for each matching identity id:
            #
            # [{ 
            #        'version_date': datetime.datetime(2011, 7, 28, 19, 15, 30, 938918), 
            #        'identity': u'1c9467fc-ac2a-47a1-b5d9-6d76a6f1cd4d'
            #  }, 
            #  {
            #        'version_date': datetime.datetime(2011, 7, 28, 19, 15, 30, 905227), 
            #        'identity': u'5f76b07b-692c-4330-afd6-05ec1cff8a37'
            #  }]
            #
            # Now we just create a query that provides these versions.
            # ORing Q objects
            latest_q = models.Q(**latest_idents[0])
            for ident in latest_idents[1:]:
                latest_q.add(models.Q(**ident), models.Q.OR)
            return instance_qs.filter(latest_q)
            #return self.model_class.objects.filter(latest_q)

class Versionable(models.Model):
    vid = models.CharField(max_length=36, primary_key=True)
    identity = models.CharField(max_length=36)
    version_date = models.DateTimeField()
    clone_date = models.DateTimeField(null=True, default=None)
    created_date = models.DateTimeField()
    
    objects = VersionManager()

    class Meta:
        abstract = True
        unique_together = ('vid', 'identity')

    def clone(self):
        # from ClonableMixin snippet (http://djangosnippets.org/snippets/1271),
        # with the pk/id change suggested in the comments
        if not self.pk:
            raise ValueError('Instance must be saved before it can be cloned')
        
        if self.clone_date:
            raise ValueError('This is a historical item and can not be cloned.')

        now = datetime.datetime.now()
        clone = copy.copy(self)
        clone.clone_date = None 
        clone.version_date = now 
        # set our source version's ID to a new UUID so the clone can 
        # get the old one -- this allows 'head' to always have the original
        # identity id allowing us to get at all historic foreign key relationships
        self.vid = unicode(uuid.uuid4())
        self.clone_date = now
        self.save()
        
        clone.save()

        # re-create ManyToMany relations
        for field in self._meta.many_to_many:
            source = getattr(self, field.attname)
            destination = getattr(clone, field.attname)
            for item in source.all():
                destination.add(item)

        clone.save()
        return clone

    @property 
    def history(self):
        return self.__class__.objects.history.filter(identity=self.identity)
    
    @property
    def current(self):
        if not self.clone_date:
            return self
        else:
            return self.__class__.objects.current.get(identity=self.identity)

class Attachment(Versionable):
    name = models.CharField(max_length=200)

    # Beacuse Attachment is a versioned resource, we tell Django not to 
    # create a reverse relationship by setting related_name to '+'. This is 
    # to ensure we can get at the correct versions of Attachments as of the 
    # time that it was cloned.
    item = models.ForeignKey('Item', related_name='+')    


class Item(Versionable):
    name = models.CharField(max_length=200)
    
    # This is a bit awkward but we want to replicate the reverse relation 
    # while giving us only the correct versions (see comments on Attachment.item).
    attachments = VersionedRelation(Attachment, 'item')

