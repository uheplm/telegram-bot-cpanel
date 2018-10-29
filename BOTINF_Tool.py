import json, os
print('BOTINF creating tool. \n* - values, nessesary for launch')
name = str(input('Enter a name for your bot* (e.g. Alexa Bot): '))
description = str(input('Enter a description for your bot: '))
lastupdate = str(input('Enter a last update date of your bot: '))
app = str(input('Enter a name of runnable file* (e.g. app.py):'))
run_env = str(input('Enter a run enviroment of your bot* (e.g. python/python3): '))
userid = str(input('Enter a your telegram userid* (write to @myidbot): '))
print('# Wrong userid may cause access error')
creator = str(input('Enter your username: '))
dataset = {'name':name,'description':description,'lastupdate':lastupdate,'app':app,'run_env':run_env,'userid':userid,'creator':creator}
newpath ='bot_' + name.replace(' ','')
if not os.path.exists(newpath):
    os.makedirs(newpath)
file = open(newpath + '/BOTINF','w')
file.write(json.dumps(dataset,indent=4))
file.close()
print('New folder named' + newpath + ' with BOTINFO was created. Place all bot resources to it.')