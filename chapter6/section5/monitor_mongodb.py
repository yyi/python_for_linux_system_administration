from __future__ import print_function
import pymongo

client = pymongo.MongoClient(host='127.0.0.1:27017')
# client.admin.authenticate('laimingxing', 'laimingxing')
rs = client.admin.command('isMaster')
print(rs)
print("ismaster:", rs['ismaster'])
print("readOnly:", rs['readOnly'])
print("num of members:", len(rs['members']))
