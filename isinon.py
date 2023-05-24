#general packages
import discord
from discord.ext import commands, tasks
import firebase_admin
import asyncio
from firebase_admin import credentials, firestore, storage

#optionals for HTML reading and time checking
import datetime
import pytz
import re
from bs4 import BeautifulSoup
import aiohttp
import io
from time import sleep

#picture mAniPulAtioN
import cv2 as cv
import numpy as np
from PIL import Image

#system manipulation
import os
import traceback
import psutil

# Use a service account
cred = credentials.Certificate('./isinon-a97281405b89.json')
firebase_admin.initialize_app(cred, {'storageBucket': 'isinon.appspot.com'})

db = firestore.client()

# bot almost acts as client = discord.Client()
botprefix = '~' #=========================================================================|

def overlayer(background, overlay, tupler):
	#https://stackoverflow.com/a/54058766/13717759 modified from code
	# slower but pastes varying alpha channels correctly
	x = int(tupler[0])
	y = int(tupler[1])

	background_width = background.shape[1]
	background_height = background.shape[0]

	if x >= background_width or y >= background_height:
		return background

	h, w = overlay.shape[0], overlay.shape[1]

	if x + w > background_width:
		w = background_width - x
		overlay = overlay[:, :w]

	if y + h > background_height:
		h = background_height - y
		overlay = overlay[:h]

	if overlay.shape[2] < 4:
		overlay = np.concatenate(
			[
				overlay,
				np.ones((overlay.shape[0], overlay.shape[1], 1), dtype = overlay.dtype) * 255
			],
			axis = 2,
		)

	overlay_image = overlay[..., :4]
	mask = overlay[..., 3:] / 255.0

	background[y:y+h, x:x+w] = (1.0 - mask) * background[y:y+h, x:x+w] + mask * overlay_image

	return background

def getprefix(bot, message):
	if message.guild != None:
		return bot.guildprefixes[str(message.guild.id)]
	else: # for DMs
		return botprefix

# intents because Discord gae
intents = discord.Intents(messages=True, guilds=True, reactions=True)

class MyBot(discord.ext.commands.Bot):
	async def close(self):
		await discord.ext.commands.Bot.change_presence(self,status=discord.Status.offline)
		newser.stop()
		print('stopping')
		await super().close()

bot = MyBot(command_prefix=getprefix, intents=intents, case_insensitive=True, status=discord.Status.offline)
bot.remove_command('help')

def embederr(msg):
	embederror = discord.Embed (
		title = 'Error',
		description = msg,
		color = discord.Colour.red(),
	)
	return embederror

def stringclean(string):
	string = string.strip(' \n')
	return string

defaultcolour = 0xcaeffe
regions = ['North & South America', 'Europe and Others', 'Asia Pacific', 'Japan']
profcolours = [0xcaeffe, 0xe74c3c, 0xe67e22, 0xf1c40f, 0x2ecc71, 0x3498db, 0x9b59b6, 0xff548d, 0xfffffe, 0x000001]
lang = ['日本語', 'English', '中文', '한국어']

for filename in os.listdir('./cogs'):
	if filename.endswith('.py'):
		bot.load_extension(f'cogs.{filename[:-3]}')

@bot.event
async def on_ready():
	print('Logged in as %s' % bot.user)

	bot.guildprefixes = {g.id:g.to_dict().get('prefix') for g in db.collection(u'servers').stream()}

	bot.supportserver = 'https://discord.gg/a34XczS'
	bot.botinviter = 'https://discord.com/api/oauth2/authorize?client_id=725507648832929885&permissions=387072&scope=bot'

	bot.codername = {
		'avatar': 'https://cdn.discordapp.com/avatars/283790768252911619/812285b2d6dfc3dbd7bb88e3890b59ea.png?size=256',
		'name': 'iShootdown™'
	}
	
	docs = db.collection(u'servers').stream()
	docs = [int(doc.id) for doc in docs]
	nonlisted = [g for g in bot.guilds if g.id not in docs]
	print(nonlisted)
	for i in nonlisted:
		db.collection(u'servers').document(u'{0}'.format(i.id)).set({ u'name': i.name, u'prefix': botprefix})
	print(f"Currently in {len(bot.guilds)} guilds")

	serverdicters = {g.id:g.to_dict() for g in db.collection(u'servers').stream()}

	if bot.user.id == 725507648832929885: # finally my stupid arse added this in
		print('Running channel check')
		serverlist = [int(i) for i in [*serverdicters]]
		chancheck = serverdicters
		for server in chancheck:
			
			if int(server) not in serverlist:
				print(f'Removed: {server}')
				db.collection(u'servers').document(f'{server}').delete()
				prefixdic = bot.guildprefixes
				del prefixdic[str(server)]
				bot.guildprefixes = prefixdic

			try:
				newslister = chancheck[server].get('newschannel')
				newslister1 = newslister
				if newslister != None:
					for k in [*newslister]:
						if bot.get_channel(int(newslister[k])) == None:
							print(f'Announcement channel {newslister[k]} from {server} {chancheck[server]["name"]} died')
							del	newslister[k]

					if newslister != newslister1:
						if newslister == {}:
							db.collection(u'servers').document(f'{server}').update({ u'newschannel': firestore.DELETE_FIELD })
						else:
							db.collection(u'servers').document(f'{server}').update({ u'newschannel': newslister })

			except (KeyError,TypeError,discord.errors.Forbidden):
				pass
				
			#try:
			#	notifs = chancheck[server].get('notifs')
			#	if notifs != None:
			#		for k in [*notifs]:
			#			if bot.get_channel(int(notifs[k])) == None:
			#				print(f'Notifs channel {notifs[k]} from {server} {chancheck[server]["name"]} died')
			#				del notifs[k]
			#
			#		if notifs == {}:
			#			db.collection(u'servers').document(f'{server}').update({ u'notifs': firestore.DELETE_FIELD })
			#		else:
			#			db.collection(u'servers').document(f'{server}').update({ u'notifs': notifs })
			#except (KeyError,TypeError,discord.errors.Forbidden):
			#	pass

	bot.startcycle = datetime.datetime.now(pytz.timezone('UTC')) + datetime.timedelta(hours=24)
	
	bot.nowstatus = discord.Status.online
	bot.nowactivity = discord.Game(name=f'SAO:MD shutting down 30/8/2021 1500 JST')
	loopstarter.start()

@tasks.loop(seconds=1,reconnect=False,count=60)
async def loopstarter():
	if int(datetime.datetime.now(pytz.timezone('UTC')).strftime('%S')) == 0:
		newser.start()
		print('Loops started')

@bot.command(brief='Help on how to use bot')
@commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True)
async def help(ctx):
	pref = getprefix(bot,ctx)
	embed = discord.Embed (
		title = 'Help Page',
		description = f':loudspeaker: Looking for commands list? Use `{pref}commands`\n[Invite {bot.user.name}]({bot.botinviter}) | [Join Support Server]({bot.supportserver})',
		colour = discord.Colour(defaultcolour)
	)
	embed.add_field(name='Change bot prefix', value=f'> `{pref}setprefix <newprefix>`', inline=False)
	langer = '\n> '.join([f'{l+1}: {lang[l]}' for l in range(len(lang))]).strip('\n')
	langstring  = f'> ```{langer}```'
	embed.add_field(name='Setting up announcement', value=f'> Use `{pref}setnotice` in the desired channel, and choose the language by enterning number. Only new announcements will be posted once it is released.\n{langstring}', inline=False)
	embed.set_footer(text=f'Coded by {bot.codername["name"]} using discord.py', icon_url=bot.codername["avatar"])
	return await ctx.send(embed=embed)

@bot.command(brief='Shows this message',name='commands')
@commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True)
async def cmdlist(ctx, cmdr:str=None, subcmdr:str=None):
	if cmdr == None and subcmdr == None:
		coggers = bot.cogs
		cogcmds = [o.get_commands() for o in list(coggers.values())]
		cognames = [*coggers]
		cogdict = {}
		for i in range(len(cognames)):
			cogdict[cognames[i]] = cogcmds[i]

		for i in [*cogdict]:
			tempname = []
			temptxt = []
			for u in cogdict[i]:
				try:
					canrun = await u.can_run(ctx)
				except (discord.ext.commands.CheckFailure, discord.ext.commands.CommandError):
					pass
				else:
					if canrun is True and u.hidden is False:
						tempname.append(u.name)
						temptxt.append(u.brief)
			
			cogdict[i] = [tempname, temptxt]
		
		for i in [*cogdict]:         
			hol = []
			cmdlist = cogdict[i][0]
			if cmdlist == []:
				del cogdict[i]
				continue
			else:
				cmddesc = cogdict[i][1]

				for o in range(len(cmdlist)):
					if cmddesc[o] != None:
						hol.append('`%s` %s' % (cmdlist[o],cmddesc[o]))
					elif cmdlist[o] != None:
						hol.append('`%s`' % (cmdlist[o]))
					else:
						continue
				
				cogdict[i] = hol

		nilcmds = []
		niltxt = []
		nilcmd = [p for p in bot.commands if p.cog is None]
		for i in nilcmd:
			try:
				canrun = await i.can_run(ctx)
			except discord.ext.commands.CommandError:
				pass
			else:
				if canrun is True and i.hidden is False:
					nilcmds.append(i.name)
					niltxt.append(i.brief)
		
		nilpara = []
		for i in range(len(nilcmds)):
			if niltxt[i] != None:
				nilpara.append('`%s` %s' % (nilcmds[i],niltxt[i]))
			else:
				nilpara.append('`%s`' % (nilcmds[i]))

		prefixprint = getprefix(bot,ctx)

		helpembed = discord.Embed (
			title = 'Commands List',
			description = f'Guild Prefix: `{prefixprint}`',
			colour = discord.Colour(defaultcolour),
		)
		for i in [*cogdict]:
			helpembed.add_field(name=i, value='\n'.join(cogdict[i]), inline=False)
		helpembed.add_field(name='General', value='\n'.join(nilpara), inline=False)
		helpembed.set_footer(text=f"Use {prefixprint}commands <command> to see more info and subcommands\nPlease don't include the <> when typing out command")
		return await ctx.send(embed=helpembed)

	else:
		cmdr = cmdr.strip(' ').lower()
		if subcmdr != None:
			subcmdr = subcmdr.strip(' ').lower()
		cmds = bot.commands
		cmdnames = [p.name for p in bot.commands]
		cmdict = dict(zip(cmdnames, cmds))

		if cmdr not in [*cmdict]:
			return await ctx.send(embed=embederr('Command does not exist.'))
		elif cmdict[cmdr].hidden is True:
			return await ctx.send(embed=embederr('CoMmaND dOeS nOt ExIst.'))
		else:
			cmd = cmdict[cmdr]
			try:
				canrun = await cmd.can_run(ctx)
			except discord.ext.commands.CommandError:
				return await ctx.send(embed=embederr('You do not have the required permissions.'))
			else:
				if canrun is not True or cmd.hidden is not False:
					return await ctx.send(embed=embederr('You do not have the required permissions.'))

		try:
			subcmds = cmd.commands
		except AttributeError:
			subcmds = None
			subcmdpara = []
			subcmdict = {}
		else:
			subcmdnames = [p.name for p in cmd.commands]
			subcmdict = dict(zip(subcmdnames, subcmds))
			subcmdpara = []
			for i in [*subcmdict]:
				if subcmdict[i] != None:
					subcmdpara.append('`%s` %s' % (i,subcmdict[i].help))
				else:
					subcmdpara.append('`%s`' % (i))

		if subcmdr != None:
			if subcmdr in [*subcmdict]:
				subcmd = subcmdict[subcmdr]
				try:
					canrun = await subcmd.can_run(ctx)
				except discord.ext.commands.CommandError:
					return await ctx.send(embed=embederr('You do not have the required permissions.'))
				else:
					if canrun is not True or subcmd.hidden is not False:
						return await ctx.send(embed=embederr('You do not have the required permissions.'))
			else:
				subcmd = None
		else:
			subcmd = None
		
		if subcmd is None:
			cmdnamer = cmd.name
			cmdhelp = cmd.help
			usager = f'{getprefix(bot,ctx)[0]}{cmd.name}'
			params = [*dict(cmd.clean_params)]
			params = ['<'+i+'>' for i in params]
			brief = cmd.brief
			
		else:
			cmdnamer = f'{cmd.name} {subcmd.name}'
			cmdhelp = subcmd.help
			usager = f'{getprefix(bot,ctx)[0]}{cmd.name} {subcmd.name}'
			params = [*dict(subcmd.clean_params)]
			params = ['<'+i+'>' for i in params]
			brief = subcmd.brief

		if subcmds != None and subcmdr is None:
			usager += ' <subcommand>'
		if params != []:
			usager += ' ' + ' '.join(params)

		usager = f'`{usager}`'

		qembed = discord.Embed (
			title = cmdnamer,
			description = cmdhelp,
			colour = discord.Colour(defaultcolour)
		)
		qembed.set_author(name='Showing help for command')
		qembed.add_field(name='Description',value=brief,inline = False)
		qembed.add_field(name='Usage',value=usager,inline = False)
		if subcmdpara != [] and subcmd is None:
			qembed.add_field(name='Subcommands available',value='\n'.join(subcmdpara),inline = False)
		
		return await ctx.send(embed=qembed)

@bot.command(brief='Support on bugs or bot usage')
@commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True)
async def support(ctx):

	infoembed = discord.Embed (
		title = 'Support Server',
		color = discord.Colour(defaultcolour),
		description = f'Click [here]({bot.supportserver}) to join support server'
	)
	infoembed.set_thumbnail(url=bot.get_guild(713910758106202132).icon_url)
	return await ctx.send(embed=infoembed)

@bot.command(brief='Account recovery/report modders for SAO:ARS')
async def suticket(ctx):
	'''Use this command to get links for support (like reporting modders or account recovery).
	There is also suggestions available below (different from support tickets)
	Make sure to choose the correct platform.'''

	ticketembed = discord.Embed (
		colour = discord.Color(defaultcolour)
	)
	ticketembed.add_field(name='Support Ticket', value='[Android](https://bnfaq.channel.or.jp/inquiry/input/1803)\n[iOS](https://bnfaq.channel.or.jp/inquiry/input/1804)', inline=False)
	ticketembed.add_field(name='Account Recovery', value='[Link](https://bncrssup.channel.or.jp/Remedies/index/PDMh)\nNote that you would be sending an email to them', inline=False)		
	ticketembed.add_field(name='Suggestions', value='[Android](https://bnfaq.channel.or.jp/opinion/input/1803)\n[iOS](https://bnfaq.channel.or.jp/opinion/input/1804)', inline=False)
	ticketembed.set_footer(text='Please choose the correct platform')
	return await ctx.send(embed=ticketembed)

@bot.event
async def on_guild_join(guild):
	print('New server joined: %s %s' % (guild.id,guild.name))
	db.collection(u'servers').document(u'{0}'.format(guild.id)).set({u'name': guild.name, u'prefix': botprefix})
	prefixdic = bot.guildprefixes
	prefixdic[str(guild.id)] = botprefix
	bot.guildprefixes = prefixdic

@bot.event
async def on_guild_remove(guild):
	print('Bot left server: %s %s' % (guild.id,guild.name))
	db.collection(u'servers').document(u'{0}'.format(guild.id)).delete()
	prefixdic = bot.guildprefixes
	del prefixdic[str(guild.id)]
	bot.guildprefixes = prefixdic

@tasks.loop(seconds=30,count=None)
async def newser():
	now_utc = datetime.datetime.now(pytz.timezone('UTC'))
	japan = now_utc.astimezone(pytz.timezone('Asia/Tokyo'))

	if newser.current_loop == 0:
		runner = True
	else:	
		if japan.hour == 15 and japan.minute <= 5:
			await bot.change_presence(status=discord.Status.dnd,activity=discord.Activity(name='MD Notices | %shelp' % botprefix,type=discord.ActivityType.listening))
			runner = True
		elif japan.hour == 0 and japan.minute <= 5:
			await bot.change_presence(status=discord.Status.dnd,activity=discord.Activity(name='MD Notices | %shelp' % botprefix,type=discord.ActivityType.listening))
			runner = True
		elif japan.minute == 0 or japan.minute == 30 or japan.minute == 15 or japan.minute == 45:
			await bot.change_presence(status=discord.Status.dnd,activity=discord.Activity(name='MD Notices | %shelp' % botprefix,type=discord.ActivityType.listening))
			runner = True
		else:
			await bot.change_presence(status=bot.nowstatus,activity=bot.nowactivity)
			runner = False

	if runner == True:
		docs = db.collection(u'servers').stream()
		newslister = [doc.to_dict().get('newschannel') for doc in docs if doc.to_dict().get('newschannel') != None]
		newsdict = {i:[] for i in ['日本語', 'English', '中文', '한국어']}
		for i in newslister:
			for k in i.keys():
				newsdict[k] = newsdict[k] + [i[k]]
		newsdict = {i:newsdict[i] for i in newsdict if newsdict[i] != []}
		langs = list(dict.fromkeys(newsdict))

		doc_ref = db.collection(u'annoucements').document(u'bot')
		doc = doc_ref.get()
		extractbot = doc.to_dict()
		oldchar = extractbot.get(u'charlinks')
		if oldchar == None:
			oldchar = []
		oldweap = extractbot.get(u'weaplinks')
		if oldweap == None:
			oldweap = []
		oldacc = extractbot.get(u'acclinks')
		if oldacc == None:
			oldacc = []
		oldall = extractbot.get(u'alinks')
		if oldall == None:
			oldall = []

		async with aiohttp.ClientSession() as session:
			async with session.get('https://api-defrag-ap.wrightflyer.net/webview/announcement?phone_type=2&lang=en') as r:
				if r.status == 200: #request OK
					mainsoup = BeautifulSoup(await r.text(),features="html.parser")
					
					everylink = [link.get('onclick') for link in mainsoup.find_all('dl', 'm_round_menu')]
					everylink = [link.partition('&')[0] for link in everylink]
					everylink = [''.join(list(link)[58:]) for link in everylink]
					everylink = list(dict.fromkeys(everylink))
					
					alink = everylink

					searchterms = db.collection(u'annoucements').document(u'searchterms').get().to_dict()

					charlink = [link for link in everylink if re.search(rf'^{searchterms["scout"]}\d+9$', link)] # set to banner previews
					charlink = list(dict.fromkeys(charlink)) #removes duplicates
					
					weaplink = [link for link in everylink if re.search(rf'^{int(searchterms["scout"])-10}\d+1$', link)] #set to weapon banners
					weaplink = list(dict.fromkeys(weaplink))

					acclink = [link for link in everylink if re.search(rf'^{searchterms["acc"]}\d+01$', link) or re.search(rf'^{searchterms["acc"]}\d+02$', link)] # set to EEE
					acclink = list(dict.fromkeys(acclink))
					
					if alink != oldall:
						print('New annoucements found')
						newall = [link for link in alink if link not in oldall]
						print(newall)
						db.collection(u'annoucements').document(u'bot').update({u'alinks': alink})
					else:
						newall = []

					if charlink != oldchar:
						print('New characters found')
						newchar = [link for link in charlink if link not in oldchar]
						db.collection(u'annoucements').document(u'bot').update({u'charlinks': charlink})
					else:
						newchar = []

					if weaplink != oldweap:  
						print('New weapons found')
						newweap = [link for link in weaplink if link not in oldweap]
						db.collection(u'annoucements').document(u'bot').update({u'weaplinks': weaplink})
						check = [link for link in newweap if link[2:4] == '99']
						if check != []:
							if check[0][0:2] == str(searchterms['scout']):
								db.collection(u'annoucements').document(u'searchterms').update({'scout': int(searchterms['scout']) + 1})
					else:
						newweap = []

					if acclink != oldacc:
						print('New accessories found')
						newacc = [link for link in acclink if link not in oldacc]
						db.collection(u'annoucements').document(u'bot').update({u'acclinks': acclink})
						check = [link for link in newacc if link[2:4] == '99']
						if check != []:
							if check[0][0:2] == str(searchterms['scout']) and check[0][-2:] == '02':
								db.collection(u'annoucements').document(u'searchterms').update({'acc': int(searchterms['acc']) + 1})
					else:
						newacc = []

					phonetyper = '&phone_type=1'
					shortlangs = {'English': 'lang=en', '中文': 'lang=tc', '한국어': 'lang=kr'}
					mainlinker = "javascript:location.href='/webview/announcement-detail?id="

					for lang in langs:
						if lang == '日本語':
							baselink = 'https://defrag-announcement.wrightflyer.net/webview/announcement-detail?id='
							noticedirect = 'https://defrag-announcement.wrightflyer.net/webview/announcement?'
							langlink = ''
						else:
							baselink = 'https://api-defrag-ap.wrightflyer.net/webview/announcement-detail?id='
							noticedirect = 'https://api-defrag-ap.wrightflyer.net/webview/announcement?'
							langlink = '&' + shortlangs[lang]

						async with session.get(url=noticedirect+phonetyper+langlink) as r:
							if r.status == 200: #request OK
								mainsoup = BeautifulSoup(await r.text(),features="html.parser")

							for link in newall:
								allsoup = mainsoup.find('dl', attrs={'onclick':mainlinker+link+phonetyper+langlink+"'"})
								if allsoup == None:
									continue
								allsoup = allsoup.find('dd')

								title = allsoup.find('h2')
								if title is None:
									title = allsoup.find('div')
								title = title.get_text()

								banner = allsoup.find_all('img')
								multibanner = False
								if len(banner) == 1:
									banner = banner[0].get('src')
									multibanner = False
								elif len(banner) > 1:
									for banno in range(len(banner)):
										async with session.get(url=banner[banno].get('src')) as artr:
											if artr.status == 200: #request OK
												artl = io.BytesIO(await artr.read())

										art = cv.imdecode(np.frombuffer(artl.read(), np.uint8),cv.IMREAD_UNCHANGED)
										art = cv.cvtColor(art,cv.COLOR_BGR2BGRA)
										if banno == 0:
											saver = art
										else:
											saver = overlayer(saver,art,(0,0))
									
									cv.imwrite(f'{lang}{link}.png',saver)
									multibanner = True
								else:
									banner = None

								period = allsoup.find('h3')
								if period != None:
									period = period.get_text()
									if period == '':
										period = None

								embed = discord.Embed (
									title = title,
									url = baselink+link+phonetyper+langlink,
									colour = discord.Colour(defaultcolour),
								)
								if period != None:
									embed.add_field(name='Period', value=period, inline=False)

								for channel in newsdict[lang]:
									channelr = bot.get_channel(int(channel))
									if channelr == None:
										continue

									try:
										if banner == None:
											await channelr.send(embed=embed)
										elif multibanner == False:
											embed.set_image(url=banner)
											await channelr.send(embed=embed)
										else:
											bannerfile = discord.File(f'{lang}{link}.png', filename=f'{lang}{link}.png')
											embed.set_image(url=f'attachment://{lang}{link}.png')
											await channelr.send(file=bannerfile,embed=embed)
									except discord.errors.Forbidden:
										try:
											await channelr.send('Bot missing permissions. Please check if bot has access to `send_messages` | `embed_links` | `attach_files`')
										except discord.errors.Forbidden:
											pass

								if multibanner == True:
									os.remove(f'{lang}{link}.png')

								if link in newchar and lang != '日本語':
									async with session.get(baselink+link+phonetyper+langlink) as r:
										if r.status == 200: #request OK
											await asyncio.sleep(1)
											newsoupr = BeautifulSoup(await r.text(),features="html.parser")
										else:
											continue
										
										newsoups = newsoupr.select('.gchaChara')

										names = []
										equipicons = []
										thumb = []
										
										for newsoup in newsoups:
											name = newsoup.select('.headTb-name')
											name = name[0].get_text()
											names.append(name)

											equipicon = newsoup.select('.headTb-icon')
											backtemp = equipicon[0].select('.attribute')
											background = backtemp[0].get('src')
											overlay = equipicon[0].select('.job')
											overlay = overlay[0].get('src')

											async with session.get(background) as bgr:
												if bgr.status == 200: #request OK
													bgl = io.BytesIO(await bgr.read())
													bg = Image.open(bgl)
													bg = bg.convert('RGBA')

											async with session.get(overlay) as ovr:
												if ovr.status == 200: #request OK
													ovl = io.BytesIO(await ovr.read())
													ov = Image.open(ovl)
													ov = ov.convert('RGBA')

											namer = newsoups.index(newsoup)
											bg.paste(ov, (13,13), ov)
											bg.save(f"{namer}.png")
											equipicons.append(f"{namer}.png")

											thumber = newsoup.select('.trimming')
											thumber = thumber[0].contents
											thumber = [i for i in thumber if i != '\n']
											thumb.append(thumber[0].get('src'))

										await asyncio.sleep(2)

										for i in range(len(names)):
											filer = discord.File(f'./{equipicons[i]}', filename=equipicons[i])
											embed = discord.Embed (
												colour = discord.Colour(defaultcolour),
											)
											embed.set_image(url=thumb[i])
											embed.set_author(name='Featured Character', url=baselink+link+phonetyper+langlink)
											embed.set_thumbnail(url=f"attachment://{equipicons[i]}")
											embed.set_footer(text='Credits to BANDAI NAMCO Entertainment Inc. and respective authors/owners \nData pulled from annoucements page. \nThis feature is still in BETA.')
											
											for channel in newsdict[lang]:
												channelr = bot.get_channel(int(channel))
												if channelr == None:
													continue
												try:
													await channelr.send(file=discord.File(equipicons[i]), embed=embed)
												except discord.errors.Forbidden:
													try:
														await channelr.send('Bot missing permissions. Please check if bot has access to `send_messages` | `embed_links` | `attach_files`')
													except discord.errors.Forbidden:
														pass

										for o in equipicons:
											os.remove(o)

								elif link in newweap:

									async with session.get(baselink+link+phonetyper+langlink) as r:
										if r.status == 200: #request OK
											await asyncio.sleep(1)
											newsoupr = BeautifulSoup(await r.text(),features="html.parser")
										else:
											continue
										
										newsoups = newsoupr.select('.gchaChara')

										names = []
										equipicons = []
										thumb = []
										atkheader = []
										atkvalue = []
										critheader = []
										critvalue = []
										bsheader = []
										bsdesc = []
										
										for newsoup in newsoups:
											name = newsoup.select('.headTb-name')
											name = name[0].get_text()
											if 'R3' not in name and 'R4' not in name:
												continue
											names.append(name)

											equipicon = newsoup.select('.headTb-icon')
											backtemp = equipicon[0].select('.attribute')
											background = backtemp[0].get('src')
											overlay = equipicon[0].select('.job')
											overlay = overlay[0].get('src')

											async with session.get(background) as bgr:
												if bgr.status == 200: #request OK
													bgl = io.BytesIO(await bgr.read())
													bg = Image.open(bgl)
													bg = bg.convert('RGBA')

											async with session.get(overlay) as ovr:
												if ovr.status == 200: #request OK
													ovl = io.BytesIO(await ovr.read())
													ov = Image.open(ovl)
													ov = ov.convert('RGBA')
											
											namer = newsoups.index(newsoup)
											bg.paste(ov, (13,13), ov)
											bg.save(f"{namer}.png")
											equipicons.append(f"{namer}.png")
											
											thumber = newsoup.select('.trimming')
											thumber = thumber[0].contents
											thumber = [i for i in thumber if i != '\n']
											thumb.append(thumber[0].get('src'))

											atk = newsoup.select('.aktA')
											atk = atk[0].get_text()
											atkheader.append(atk)
											
											atk = newsoup.select('.aktA-b')
											atk = atk[0].get_text()
											atkvalue.append(atk)

											crit = newsoup.select('.criA')
											crit = crit[0].get_text()
											critheader.append(crit)
											
											crit = newsoup.select('.criA-b')
											crit = crit[0].get_text()
											critvalue.append(crit)

											bs = newsoup.select('.mpA')
											bs = bs[0].get_text()
											bsheader.append(bs)
											
											bs = newsoup.select('.mpA-b')
											bs = stringclean(bs[0].decode_contents())
											bs = bs.split('<br>')
											bs = '\n'.join(bs)
											bs = bs.split('<br/>')
											bs = '\n'.join(bs)
											bs = bs.strip('\n ')
											
											bs = bs.split(' ')
											bs = ['&' if x=="&amp;" else x for x in bs]
											bs = ' '.join(bs)

											bsdesc.append(bs)

										print(names)
										print(equipicons)
										print(thumb)
										print(atkheader)
										print(atkvalue)
										print(critheader)
										print(critvalue)
										print(bsheader)
										print(bsdesc)

										await asyncio.sleep(2)

										for i in range(len(names)):
											filer = discord.File(f'./{equipicons[i]}', filename=equipicons[i])
											embed = discord.Embed (
												title = names[i],
												colour = discord.Colour(defaultcolour),
											)
											embed.set_image(url=thumb[i])
											embed.set_author(name='New weapon in banner', url=baselink+link+phonetyper+langlink)
											embed.set_thumbnail(url=f"attachment://{equipicons[i]}")
											embed.add_field(name=atkheader[i], value=atkvalue[i], inline=True)
											embed.add_field(name=critheader[i], value=critvalue[i], inline=True)
											embed.add_field(name=bsheader[i], value=bsdesc[i], inline=False)
											embed.set_footer(text='Credits to BANDAI NAMCO Entertainment Inc. and respective authors/owners \nData pulled from annoucements page. \nThis feature is still in BETA.')
											for channel in newsdict[lang]:
												channelr = bot.get_channel(int(channel))	
												if channelr == None:
													continue

												try:
													await channelr.send(file=discord.File(equipicons[i]), embed=embed)
												except discord.errors.Forbidden:
													try:
														await channelr.send('Bot missing permissions. Please check if bot has access to `send_messages` | `embed_links` | `attach_files`')
													except discord.errors.Forbidden:
														pass

										for i in equipicons:
											os.remove(i)

								elif link in newacc:
									async with session.get(baselink+link+phonetyper+langlink) as r:
										if r.status == 200: #request OK
											await asyncio.sleep(1)
											newsoupr = BeautifulSoup(await r.text(),features="html.parser")
										else:
											continue
										
										newsoups = newsoupr.select('.gchaChara')

										names = []
										equipicons = []
										thumb = []
										skillheader = []
										skillvalues = []
										
										for newsoup in newsoups:
											name = newsoup.select('.headTb-name')
											name = name[0].get_text()
											if 'R2~4' not in name:
												continue
											names.append(name)

											equipicon = newsoup.select('.headTb-icon')
											backtemp = equipicon[0].select('.attribute')
											background = backtemp[0].get('src')
											overlay = equipicon[0].select('.job')
											overlay = overlay[0].get('src')

											async with session.get(background) as bgr:
												if bgr.status == 200: #request OK
													bgl = io.BytesIO(await bgr.read())
													bg = Image.open(bgl)
													bg = bg.convert('RGBA')

											async with session.get(overlay) as ovr:
												if ovr.status == 200: #request OK
													ovl = io.BytesIO(await ovr.read())
													ov = Image.open(ovl)
													ov = ov.convert('RGBA')
											
											namer = newsoups.index(newsoup)
											bg.paste(ov, (13,13), ov)
											bg.save(f"{namer}.png")
											equipicons.append(f"{namer}.png")
											
											thumber = newsoup.select('.trimming')
											thumber = thumber[0].contents
											thumber = [i for i in thumber if i != '\n']
											thumb.append(thumber[0].get('src'))

											skillsoup = newsoup.find_all(class_='skill', limit=2)

											skillheads = [i.find('td',attrs={"width":"20%"}) for i in skillsoup]
											skillval = [i.find_next_sibling() for i in skillheads]

											skillheads = [i.get_text() for i in skillheads]
											skillval = [i.decode_contents() for i in skillval]
											skillval = [i.replace('<br/>', '\n') for i in skillval]
											skillval = [i.replace('<br>', '\n') for i in skillval]
											skillval = [i.strip('\n ') for i in skillval]
											skillheader.append(skillheads)
											skillvalues.append(skillval)

										print(names)
										print(equipicons)
										print(thumb)
										print(skillheader)
										print(skillvalues)

										await asyncio.sleep(2)

										for i in range(len(names)):
											filer = discord.File(f'./{equipicons[i]}', filename=equipicons[i])
											embed = discord.Embed (
												title = names[i],
												colour = discord.Colour(defaultcolour),
											)
											embed.set_image(url=thumb[i])
											embed.set_author(name='New equipment in Equip Exchange Event', url=baselink+link+phonetyper+langlink)
											embed.set_thumbnail(url=f"attachment://{equipicons[i]}")
											for u in range(len(skillheader)):
												embed.add_field(name=skillheader[i][u], value=skillvalues[i][u], inline=False)
											embed.set_footer(text='Credits to BANDAI NAMCO Entertainment Inc. and respective authors/owners \nData pulled from annoucements page. \nThis feature is still in BETA.')
											
											for channel in newsdict[lang]:
												channelr = bot.get_channel(int(channel))
												if channelr == None:
													continue
												try:
													await channelr.send(file=discord.File(equipicons[i]), embed=embed)
												except discord.errors.Forbidden:
													try:
														await channelr.send('Bot missing permissions. Please check if bot has access to `send_messages` | `embed_links` | `attach_files`')
													except discord.errors.Forbidden:
														pass

										for i in equipicons:
											os.remove(i)

@bot.command(brief='Delete your data stored on bot')
@commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True)
async def deldata(ctx):
	'''**WARNING! CLEARING YOUR DATA WILL REMOVE FRIEND ID FROM BOT IF SET!**
	
	This command will show and give you the option to delete your data.'''

	def verify(m):
		return m.author.id == ctx.author.id

	databaser = db.collection('players').document(f'{ctx.author.id}').get()
	if databaser.exists:
		databaser = databaser.to_dict()
	else:
		return await ctx.send(embed=embederr('No data found.'))

	datas = [f'{data}: {databaser[data]}' for data in [*databaser]]
	datas = '\n'.join(datas)

	ticketembed = discord.Embed (
		description = '**WARNING! CLEARING YOUR DATA WILL REMOVE FRIEND ID FROM BOT IF SET!**',
		colour = discord.Color(defaultcolour),
		title = 'User Data Deletion'
	)
	ticketembed.add_field(name='Your current data stored', value=f"```{datas}```", inline=False)
	ticketembed.add_field(name='Proceed with data deletion?', value='Enter `y` to proceed with deletion or `n` to cancel' , inline=False)
	botmsg = await ctx.send(embed=ticketembed)

	try:
		msginput = await bot.wait_for('message', check=verify, timeout=40.0)
	except asyncio.TimeoutError:
		print('timeout')
		return await botmsg.edit(embed=embederr('User took too long!'))
		
	if msginput.content.lower() == 'y':
		blob = storage.bucket().blob(databaser['image'])
		blob.delete()
		db.collection('players').document(f'{ctx.author.id}').delete()
		print(f'User {ctx.author} {ctx.author.id} deleted data from bot.')
		ticketembed = discord.Embed (
			description = 'Data deletion complete',
			colour = discord.Color.green()
		)
		await msginput.delete()
		return await botmsg.edit(embed=ticketembed)
	else:
		print(f'User {ctx.author} cancelled.')
		ticketembed = discord.Embed (
			description = 'Operation cancelled by user',
			colour = discord.Color.red()
		)
		await msginput.delete()
		return await botmsg.edit(embed=ticketembed)

@bot.command(brief='Shows bot info')
@commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True)
async def botinfo(ctx):

	infoembed = discord.Embed (
		title = 'iSinon Info',
		color = discord.Colour(defaultcolour),
		description = f'''iSinon is for the SAO:MD community to improve the Discord experience.

		Features:
		• Annoucements directly from MD annoucements page
		• New character/weapon/armour/accessory details (stats/skills)
		• MD friend ID profiles

		If bot doesn't respond for awhile, there is an update so please wait for a few minutes.
		If bot is offline, probably due to serious error that needs a few hours to fix.
		For support with bot usage/bugs/suggestions, contact me using {getprefix(bot,ctx)}support and join server link.

		Useful links:
		[SAO:ARS official community server](https://discord.gg/QuZwZBw)
		[SAO:MD official community server](https://discord.gg/memorydefrag)
		[SAO:IF official community server](https://discord.gg/integralfactor)''',
	)
	infoembed.set_footer(text='Coded by %s using discord.py' % bot.codername['name'],icon_url=bot.codername["avatar"])
	
	return await ctx.send(embed=infoembed)

@bot.command(brief='Invite iSinon to your server')
@commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True)
async def invite(ctx):
	notiembed = discord.Embed (
		title = f'Invite {bot.user.name}',
		color = discord.Colour(defaultcolour),
		description = f'Click [here]({bot.botinviter}) to invite.\nPlease ensure all permissions are allowed.',
	)
	notiembed.set_thumbnail(url=bot.user.avatar_url)
	return await ctx.send(embed=notiembed)

@bot.command(brief='See bot server configs/bot stats')
@commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True)
async def botstats(ctx):
	'''Due to current limitations, bot will reset once every 24h +~216mins.\nThis command will show time till cycling and server configurations.'''
	serverdict = db.collection(u'servers').document(str(ctx.guild.id)).get()
	if serverdict.exists:
		serverdict = serverdict.to_dict()
	else:
		serverdict = {}

	now_utc = datetime.datetime.now(pytz.timezone('UTC'))

	s = (bot.startcycle - now_utc).total_seconds()
	if s > 0:
		days, remainder = divmod(s, 86400)
		hours, remainder = divmod(remainder, 3600)
		minutes, remainder = divmod(remainder, 60)
		timeleft = '{:02}h {:02}min'.format(int(hours), int(minutes))
	else:
		timeleft = 'Bot refreshing soon...'

	try:
		newslister = serverdict['newschannel']
	except KeyError:
		noticetext = 'None'
	else:
		noticetext = '\n'.join([f"{u}: {bot.get_channel(newslister[u]).mention}" for u in newslister])

	infoembed = discord.Embed(
		title = f'{bot.user.name} Bot Info',
		colour = discord.Color(defaultcolour)
	)
	infoembed.add_field(name='Quick Refresh in..',value=f'`{timeleft}`',inline=True)
	infoembed.add_field(name='Memory Usage',value=f'`{psutil.virtual_memory().percent}%`',inline=True)
	infoembed.add_field(name='Server Count',value=f'`{len(bot.guilds)}`',inline=True)
	infoembed.add_field(name='Server Prefix',value=f'`{getprefix(bot,ctx)}`',inline=False)
	infoembed.add_field(name='Notice Channels',value=f'{noticetext}',inline=True)
	infoembed.set_footer(text='Coded by %s using discord.py' % bot.codername['name'],icon_url=bot.codername["avatar"])
	return await ctx.send(embed=infoembed)

@bot.event
async def on_guild_update(before,after):
	doc = db.collection(u'servers').document(u'{0}'.format(after.id)).get()
	if doc.exists:
		if before.name != after.name:
			db.collection(u'servers').document(u'{0}'.format(after.id)).update({ u'name': after.name })
	else:
		doc = db.collection(u'servers').document(u'{0}'.format(after.id)).set({u'name':after.name, u'prefix':botprefix})

@bot.event
async def on_command(ctx):
	if ctx.guild == None:
		print(f'{ctx.author} from DMs used {ctx.command} at {ctx.message.created_at}')
	else:
		print(f'{ctx.author} from {ctx.guild.name} used {ctx.command} at {ctx.message.created_at}')

@bot.command(hidden=True)
@commands.is_owner()
async def botleave(ctx):
	
	for i in [*bot.guildprefixes]:
		if i != 713910758106202132:
			guild = bot.get_guild(int(i))
			await guild.leave()

@bot.command(hidden=True)
@commands.is_owner()
async def oops(ctx):
	newschannels = [i.to_dict().get('newschannel') for i in db.collection('servers').stream() if i.to_dict().get('newschannel') is not None]
	channels = []
	for i in newschannels:
		channels = channels + list(i.values())

	channels = list(dict.fromkeys(channels))
	print(channels)

	embed = discord.Embed(
		title = 'Closure of iSinon service',
		description = f"SAO:MD will be closing to offline mode.\n\nHence, this bot will be terminating service immediately, leaving all servers and this bot will be deleted.\n\nIf you want to still scout MD characters on a bot, you can [invite iSAO](https://discord.com/api/oauth2/authorize?client_id=741199020461916180&permissions=387072&scope=bot) to your server.\n\nThank you for using iSinon\n- iShootdown"
	)
	embed.set_author(name='Important Message')
	for i in channels:
		if bot.get_channel(i) != None:
			channel = bot.get_channel(i)
			try:
				await channel.send(embed=embed)
				print(f'Sent to {channel} in {channel.guild}')
			except discord.errors.Forbidden:
				continue

@bot.command(hidden=True)
@commands.is_owner()
async def testrun(ctx):
	docs = db.collection(u'servers').stream()
	newsdict = {'日本語': [775153221709987850], 'English': [775153221709987850], '中文': [775153221709987850], '한국어': [775153221709987850]}
	langs = list(dict.fromkeys(newsdict))

@bot.event
async def on_command_error(ctx,error):
	if ctx.guild == None:
		guilder = 'DMs'
	else:
		guilder = ctx.guild.name

	print(f'{error} from {guilder}')
	traceback.print_tb(error.__traceback__)

	if isinstance(error, commands.CommandInvokeError):
		error = error.original

	errorstr = None
	footerstr = None

	if isinstance(error, commands.NotOwner):
		errorstr = 'Owner only command.'
	elif isinstance(error, commands.NoPrivateMessage):
		errorstr = 'Guild only command.'
	elif isinstance(error, commands.MissingRequiredArgument):
		missingargs = error.param
		errorstr = 'Missing `%s` parameter.' % missingargs
		footerstr = f"Use {getprefix(bot,ctx)}commands {ctx.command.name} for usage info"
	elif isinstance(error, commands.BotMissingPermissions):
		missingperms = error.missing_perms
		errorstr = f'Bot missing permission `{" | ".join(missingperms)}`.'
		footerstr = f"Use {getprefix(bot,ctx)}commands {ctx.command.name} for usage info"
	elif isinstance(error, commands.MissingPermissions):
		missingperms = error.missing_perms
		errorstr = f'User missing permission `{" | ".join(missingperms)}`.'
	elif isinstance(error, commands.CommandNotFound):
		invokedcmd = str(error).split(' ')[1].strip('"')
		if invokedcmd.isalpha() == True:
			errorstr = f'Command `{invokedcmd}` is not found.'
			footerstr = f"Use {getprefix(bot,ctx)}help or {getprefix(bot,ctx)}commands for valid commands"
	else:
		errorstr = f'Unexpected error has occurred.'
		footerstr = f'Dev notified of error. You can check updates via {getprefix(bot,ctx)}support.'

	try:
		if errorstr is not None:
			embedrr = embederr(errorstr)
			if footerstr is not None:
				embedrr.set_footer(text=footerstr)
			return await ctx.send(embed=embedrr)
	except discord.errors.Forbidden:
		errorembed = discord.Embed (
			title = 'Bot missing permissions',
			colour = discord.Colour.red(),
			description = '`send_messages` | `embed_links`'
		)
		if errorstr is not None:
			errorembed.add_field(name='Additional errors',value=errorstr,inline=False)
		errorembed.set_footer(text="If you don't have permissions to edit permissions for bot, please contact your server moderators")
		return await ctx.author.send(embed=errorembed)

#=========================================================================|
bot.run(None) # redacted
