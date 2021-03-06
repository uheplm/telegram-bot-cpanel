#!/usr/bin/python
from subprocess import Popen,PIPE
import config as cfg
from io import BytesIO
import sys
import subprocess
import signal
import telebot
from telebot import types
import os, sys
import strings
import shlex
import json
import atexit
import time, datetime
import zipfile
import requests

API_TOKEN = cfg.API_TOKEN # api token from @BotFather
BOT_SUPERADMIN = cfg.BOT_SUPERADMIN # id of owner of bot

bot = telebot.TeleBot(API_TOKEN,threaded = False)

def Terminate():
	''' Kills all child processes when bot stops '''
	os.killpg(os.getpid(), signal.SIGTERM)

def sec2time(sec, n_msec=0):
    ''' Convert seconds to 'D days, HH:MM:SS.FFF' '''
    if hasattr(sec,'__len__'):
        return [sec2time(s) for s in sec]
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    if n_msec > 0:
        pattern = '%%02d:%%02d:%%0%d.%df' % (n_msec+3, n_msec)
    else:
        pattern = r'%02d:%02d:%02d'
    if d == 0:
        return pattern % (h, m, s)
    return ('%d days, ' + pattern) % (d, h, m, s)

def getBots():
	''' 
	# Looking for folders with name starts with \"bot_\"
	# and also checks BOTFILE for errors.
	# For generating BOTFILE use BOTFILE_tool.py
	'''
	bot_list = {}
	bot_folders = list(filter(lambda x: os.path.isdir(x) and x.startswith('bot_'), os.listdir('.')))
	for i in bot_folders:
		try:
			botinf = json.loads(open(i + "/BOTINF").read())
			if 'name' in botinf and 'description' in botinf and 'lastupdate' in botinf and 'name' in botinf and 'app' in botinf and 'run_env' in botinf and 'userid' in botinf and 'creator' in botinf:
				bot_list[i] = botinf
				print('Bot ' + i + ' loaded')
			else:
				print('Error occured while adding ' + i + ': BOTINF file has no one or more nessesary parameters')
		except Exception as e:
			print('Error occured while adding ' + i + ': ' + str(e))
			continue

	return bot_list

running = {}
runtime = {}

bots = getBots()

@bot.message_handler(content_types = ['document'])
def deployBot(msg):
	'''
	# When superadmin sends .zip file to bot
	# unpacking it and cheking BOTINF file for errors
	# then installing it
	'''
	global bots
	print(msg.document.file_id)
	if msg.document.file_name.startswith('bot_') and msg.document.mime_type == 'application/zip':
		if msg.from_user.id == BOT_SUPERADMIN:
			try:
				file_info = bot.get_file(msg.document.file_id)
				file = open('TEMP/tempfile','wb')
				file.write(bot.download_file(file_info.file_path))
				file.close()
				zip_file = zipfile.ZipFile('TEMP/tempfile', 'r')
				zip_file.extract('BOTINF',path = 'TEMP/')
				botinfo = json.loads(open('TEMP/BOTINF','r').read())
				if 'name' in botinfo and 'description' in botinfo and 'lastupdate' in botinfo and 'app' in botinfo and 'run_env' in botinfo and 'userid' in botinfo and 'creator' in botinfo:
					bot.reply_to(msg,strings.botcarddeploy.format(botinfo['name'],botinfo['description'],botinfo['lastupdate'],botinfo['app'],botinfo['creator']), parse_mode = 'html')
					zip_file.extractall(msg.document.file_name.replace('.zip',''))
				else:
					bot.reply_to(msg,'Error occured while adding ' + msg.document.file_name + ': BOTINF file has no one or more nessesary parameters')
			except Exception as e:
				bot.reply_to(msg,'Error occured while adding ' + msg.document.file_name + ': ' + str(e))
			bots = getBots()
		else:
			bot.reply_to('You can\'t deploy bots. Please, write to @GrZd')

@bot.message_handler(commands = ['reload'])
def reload(msg):
	''' Reloading the list of bots '''
	global bots
	bots = getBots()
	bot.reply_to(msg,'BotList was reloaded')

@bot.message_handler(commands = ['start'])
def listof(msg):
	''' Sends greetings message to user when /start '''
	keyboard = types.InlineKeyboardMarkup()
	keyboard.add(types.InlineKeyboardButton(text = 'Next step', callback_data='$list'))
	bot.send_message(msg.from_user.id,strings.botinfocard,reply_markup = keyboard)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
	''' Global handler of inline buttons '''
	if call.message:
		if call.data.startswith('$ob_'):
			''' 
			# ob means observe bot.
			# When button is pressed, sends detailed info about bot
			# and controls for it
			'''
			bot.answer_callback_query(call.id,'Processing...',show_alert = False)
			botname = call.data.replace('$ob_','')
			isrunning = (running[botname].poll() == None) if botname in running else False
			keyboard = types.InlineKeyboardMarkup()
			if botname in running and isrunning:
				keyboard.row(types.InlineKeyboardButton(text=strings.stopbtn, callback_data='$kb_' + botname),types.InlineKeyboardButton(text=strings.relaunch, callback_data='$rlb_' + botname))			
			else:
				keyboard.add(types.InlineKeyboardButton(text=strings.runbtn, callback_data='$rb_' + botname))
			keyboard.row(types.InlineKeyboardButton(text=strings.rload, callback_data='$ob_' + botname),types.InlineKeyboardButton(text=strings.goback, callback_data='$list'))
			keyboard.add(types.InlineKeyboardButton(text=strings.files, callback_data='$gf_' + botname))
			if not botname in running:
				bot.edit_message_text(chat_id = call.from_user.id,message_id = call.message.message_id, text = strings.botcard.format(bots[botname]['name'],bots[botname]['description'],bots[botname]['lastupdate'],bots[botname]['app'],bots[botname]['creator']) + (('\n' + strings.running.format(str(running[botname].pid),sec2time(time.time() - runtime[botname]) if botname in running else '0')) if botname in running else ''),parse_mode = 'html',reply_markup = keyboard)
			else:
				if not isrunning:
					bot.edit_message_text(chat_id = call.from_user.id,message_id = call.message.message_id, text = strings.bot_exit.format(running[botname].communicate()[1] if botname in running else 'Not started yet',sec2time(time.time() - runtime[botname])),reply_markup = keyboard)
					del running[botname]
					del runtime[botname]
				else:
					bot.edit_message_text(chat_id = call.from_user.id,message_id = call.message.message_id, text = strings.botcard.format(bots[botname]['name'],bots[botname]['description'],bots[botname]['lastupdate'],bots[botname]['app'],bots[botname]['creator']) + (('\n' + strings.running.format(str(running[botname].pid),sec2time(time.time() - runtime[botname]) if botname in running else '0')) if botname in running else ''),parse_mode = 'html',reply_markup = keyboard)
		
		elif call.data.startswith('$rb_'):
			'''
			# rb means run bot.
			# When button is presseed
			# creating subprocess with bot 
			# and returning to user PID of this subprocess
			'''
			bot.answer_callback_query(call.id,'Processing...',show_alert = False)
			botname = call.data.replace('$rb_','')
			botwd = os.getcwd() + '/' + botname
			process = Popen(shlex.split(bots[botname]['run_env'] + ' ' + botwd + '/' + bots[botname]['app']), cwd = botwd, env={"PYTHONPATH": ":".join(sys.path)},stdout=PIPE,stderr=PIPE)
			running[botname] = process
			runtime[botname] = int(time.time())
			keyboard = types.InlineKeyboardMarkup()
			keyboard.add(types.InlineKeyboardButton(text=strings.stopbtn, callback_data='$kb_' + botname))
			keyboard.row(types.InlineKeyboardButton(text=strings.back_to, callback_data='$ob_' + botname),types.InlineKeyboardButton(text=strings.goback, callback_data='$list'))
			bot.edit_message_text(chat_id = call.from_user.id,message_id = call.message.message_id, text = strings.started.format(bots[botname]['name'],str(process.pid)),reply_markup = keyboard,parse_mode = 'html')
		elif call.data.startswith('$kb_'):
			'''
			# kb means kill bot.
			# When button is pressed
			# send SIGKILL to bot\'s subprocess,
			# removing it from running list and 
			# show runtime to user
			'''
			bot.answer_callback_query(call.id,'Processing...',show_alert = False)
			botname = call.data.replace('$kb_','')
			try:
				os.kill(running[botname].pid, signal.SIGKILL)
				del running[botname]
			except:
				print('OOPS')
			keyboard = types.InlineKeyboardMarkup()
			keyboard.add(types.InlineKeyboardButton(text=strings.relaunch, callback_data='$rb_' + botname))
			keyboard.row(types.InlineKeyboardButton(text=strings.back_to, callback_data='$ob_' + botname),types.InlineKeyboardButton(text=strings.goback, callback_data='$list'))
			bot.edit_message_text(chat_id = call.from_user.id,message_id = call.message.message_id, text = strings.stopped.format(botname,(sec2time(int(time.time()) - int(runtime[botname])) if botname in runtime else '0')),parse_mode = 'html',reply_markup = keyboard)
			if botname in runtime:
				del runtime[botname]
		elif call.data.startswith('$list'):
			'''
			# Sends to user a list of bots
			'''
			bot.answer_callback_query(call.id,'Processing...',show_alert = False)
			keyboard = types.InlineKeyboardMarkup()
			count = 0
			for i in bots:
				if str(call.from_user.id) in bots[i]['userid']:
					count += 1
					keyboard.add(types.InlineKeyboardButton(text=('▶️️ ' if i in running else '') + bots[i]['name'], callback_data='$ob_' + i))
			if count == 0:
				keyboard.add(types.InlineKeyboardButton(text=strings.add_bot, callback_data='$addb'))
			bot.edit_message_text(chat_id = call.from_user.id,message_id = call.message.message_id, text = strings.botlist.format(len(running),count),parse_mode = 'html',reply_markup = keyboard)
		elif call.data.startswith('$rlb_'):
			'''
			# rlb means relaunch bot
			'''
			bot.answer_callback_query(call.id,'Processing...',show_alert = False)
			botname = call.data.replace('$rlb_','')
			if botname in running:
				try:
					os.kill(running[botname].pid, signal.SIGKILL)
					del running[botname]
				except:
					print('OOPS')
			if botname in runtime:
				del runtime[botname]
			botwd = os.getcwd() + '/' + botname
			process = Popen(shlex.split(bots[botname]['run_env'] + ' ' + botwd + '/' + bots[botname]['app']), cwd = botwd, env={"PYTHONPATH": ":".join(sys.path)},stdout=PIPE,stderr=PIPE)
			running[botname] = process
			runtime[botname] = int(time.time())
			keyboard = types.InlineKeyboardMarkup()
			keyboard.add(types.InlineKeyboardButton(text=strings.stopbtn, callback_data='$kb_' + botname),types.InlineKeyboardButton(text=strings.relaunch, callback_data='$rlb_' + botname))
			keyboard.row(types.InlineKeyboardButton(text=strings.back_to, callback_data='$ob_' + botname),types.InlineKeyboardButton(text=strings.goback, callback_data='$list'))
			bot.edit_message_text(chat_id = call.from_user.id,message_id = call.message.message_id, text = strings.restarted.format(bots[botname]['name'],str(process.pid)),reply_markup = keyboard,parse_mode = 'html')
		elif call.data.startswith('$addb'):
			''' 
			#addb means addbot
			'''
			keyboard = types.InlineKeyboardMarkup()
			keyboard.add(types.InlineKeyboardButton(text = 'Write to GrZd',url = 'tg://resolve?domain=Gr_Zd'))
			keyboard.add(types.InlineKeyboardButton(text = strings.goback, callback_data = '$list'))
			bot.send_document(call.from_user.id,'BQADAgADMwIAAvM98EsvtVRol7AeQgI')
			bot.edit_message_text(chat_id = call.from_user.id,message_id = call.message.message_id, text = strings.add_help, reply_markup = keyboard, parse_mode = 'html')
		elif call.data.startswith('$gf_'):
			'''
			# gf means get files
			# sends to a user list of files in folder of bot
			'''
			bot.answer_callback_query(call.id,'Processing...',show_alert = False)
			botname = call.data.replace('$gf_','')
			keyboard = types.InlineKeyboardMarkup()
			botfiles = list(filter(lambda x: not os.path.isdir(x), os.listdir(botname)))
			for i in botfiles:
				keyboard.add(types.InlineKeyboardButton(text = i, callback_data = '$of_' + botname + '/' + i))
			keyboard.add(types.InlineKeyboardButton(text = strings.back_to, callback_data = "$ob_" + botname))
			bot.edit_message_text(chat_id = call.from_user.id,message_id = call.message.message_id, text = strings.filestext.format(), reply_markup = keyboard, parse_mode = 'html')
		elif call.data.startswith('$of_'):
			'''
			# of means open file
			# sends to user a file, selected by gf
			'''
			bot.answer_callback_query(call.id,'Processing...',show_alert = False)
			filename = call.data.replace('$of_','')	
			bot.send_document(call.from_user.id,open(filename,'rb'))

atexit.register(Terminate)
def telegram_polling():
	''' 
	# Try to relaunch bot after crash
	'''
    try:
        bot.polling(none_stop=True, timeout=60)
    except Exception as e:
        bot.stop_polling()
        time.sleep(10)
        print('Error: ' + str(e))
        telegram_polling()

if __name__ == '__main__':    
    telegram_polling()