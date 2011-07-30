import unittest
from django.test import TestCase 
from dirtyversion.versions import models 

class VersionTest(TestCase):

    def setUp(self):
        self.item = models.Item.objects.create(name='First identity')

    def test_clone(self):
        '''Ensure that clone creates a new item with the same 
        identity ID.'''
        self.assertEqual(self.item.vid, self.item.identity)
        clone = self.item.clone()
        self.assertEqual(clone.created_date, self.item.created_date)
        self.assertNotEqual(clone.version_date, self.item.version_date)
        self.assertEqual(clone.name, self.item.name)
        self.assertEqual(clone.identity, self.item.identity)
        self.assertNotEqual(clone.vid, self.item.vid)

    def test_managers(self):
        '''Test that the managers work as expected.'''

        # make 5 new versions and collect names to later compare with the
        # set of names retrieved from history
        names = []
        names.append(self.item.name)
        for i in range(5):
            # get() should work because there should only be one Item with this 
            # identity that has a null modified_date (via CurrentVersionManager)
            # if this is not the case we can assume a programming error (?)
            item = models.Item.objects.current.get(identity=self.item.identity) 
            clone = item.clone()
            clone.name = 'Thing {}'.format(i)
            clone.save()
            if i < 4:
                names.append(clone.name)

        item = models.Item.objects.current.get(identity=self.item.identity) 
        current_count = models.Item.objects.current.count() 

        # there should only be one item available at the given identity
        # for the default manager
        self.assertEqual(current_count, 1)
        # the previous 5 revisions can be accessed through the history property
        self.assertEqual(item.history.count(), 5)
        
        # make sure we can't clone a historical item
        with self.assertRaises(ValueError):
            broken = item.history[0].clone()

        # get the latest identity or "head revision"
        latest = models.Item.objects.current.get(identity=self.item.identity)
        self.assertEqual(latest.name, 'Thing 4')
       
        # ensure the 'current' property works so we can get at the current head
        # revision from historical revisions
        self.assertEqual(latest.history[0].current.vid, latest.vid)
        
        # ensure latest is not in history
        with self.assertRaises(models.Item.DoesNotExist):
            latest.history.get(vid=latest.vid)
        
        hist_names = latest.history.values_list('name', flat=True)
        self.assertEqual(set(names), set(hist_names))

    def test_relationships(self):
        '''Ensure that versions of objects only reference correct instances of related
        versioned objects.'''
        
        # let's add an attachment to our original item
        att = models.Attachment.objects.create(name="Attached to you", item=self.item)
        
        item = models.Item.objects.current.get(identity=self.item.identity)
        self.assertEqual(item.attachments.count(), 1)

        # let's modify the item creating a new revision 
        item_clone = self.item.clone()
        item_clone.name = 'Better Name'
        item_clone.save()
        
        # and add a new attachment 
        new_att = models.Attachment.objects.create(name="Second Attachment (no revisions)", item=item_clone)
        
        # just make sure that we aren't clobbering a separate identity
        self.assertNotEqual(att.identity, new_att.identity)

        # refresh from DB ensuring the clone is the latest
        # by calling get() with its id and check that it 
        # references 2 attachments.
        item = models.Item.objects.current.get(vid=item_clone.vid)
        self.assertEqual(item.attachments.count(), 2)        
        self.assertEqual(item.attachments.latest('created_date').name, new_att.name)

        # add some revisions to Attachment new_att
        for i in range(3):
            revatt = models.Attachment.objects.current.get(identity=new_att.identity) 
            revclone = revatt.clone()
            revclone.name = 'Revision {}'.format(i)
            revclone.save()
        
        # ensure that the identity id and the version id of the 'head' are the same
        # after adding the revisions
        latest = models.Item.objects.current.get(identity=self.item.identity)
        self.assertEqual(item.vid, latest.vid)
        
        # there should still only be 2 'current' attachments
        self.assertEqual(latest.attachments.count(), 2)

        # check that we have correct history on the latest attachment
        latest_att = latest.attachments.latest('created_date')
        self.assertEqual(latest_att.history.count(), 3)

        # check names 
        self.assertEqual(latest_att.name, 'Revision 2')        
        att_names = latest.attachments.values_list('name', flat=True)
        self.assertTrue(new_att.name not in att_names)
        self.assertTrue(att.name in att_names)
        self.assertEqual(latest_att.history.reverse()[0].name, 'Second Attachment (no revisions)')
        
        # clone the item again 
        self.assertEqual(latest.history.count(), 1)
        latest_clone = latest.clone()
        latest_clone.name = 'Best Name'
        latest_clone.save()
        self.assertEqual(latest.history.count(), 2)
        
        # refresh from the db again just in case
        latest = models.Item.objects.current.get(identity=self.item.identity)
        
        # check that the original revision references only the original attachment
        first = latest.history.reverse()[0]
        self.assertEqual(first.attachments.count(), 1) 
        first_att = first.attachments[0] 
        
        # ensure that there is no history on the attachment
        self.assertEqual(first_att.history.count(), 0) 
        self.assertIsNone(first_att.clone_date) 
        self.assertEqual(first_att.name, att.name)
        
        # this is getting deep, I know, but bear with me
        #
        # let's add a new revision to the first attachment and ensure that 
        # the revision does not show up for any of the items in history
        first_att_clone = first_att.clone()
        self.assertTrue(first_att_clone.version_date > first.version_date)
        self.assertTrue(first_att_clone.version_date > att.version_date)
        first_att_clone.name = 'Modified First Attachment'
        first_att_clone.save()
        
        # Now, lets make sure that this change shows up only for the most recent version 
        # of the item. 
        self.assertEqual(first.attachments.count(), 1)
        self.assertNotEqual(first.attachments[0].name, first_att_clone.name)
        
        for h in latest.history:
            self.assertTrue(first_att_clone.name not in h.attachments.values_list('name', flat=True))

        self.assertTrue(first_att_clone.name in latest.attachments.values_list('name', flat=True))
        
