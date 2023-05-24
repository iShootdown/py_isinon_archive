import discord
from discord.ext import commands
import asyncio
from firebase_admin import firestore
# Use a service account

db = firestore.client()
botprefix = '~'

def embederr(msg):
	embederror = discord.Embed (
		title = 'Error',
		description = str(msg),
		color = discord.Colour.red(),
	)
	return embederror

def getprefix(bot, message):
	if message.guild != None:
		return bot.guildprefixes[str(message.guild.id)]
	else: # for DMs
		return botprefix

defaultcolour = 0xcaeffe
regions = ['North & South America', 'Europe and Others', 'Asia Pacific', 'Japan']
profcolours = [0xcaeffe, 0xe74c3c, 0xe67e22, 0xf1c40f, 0x2ecc71, 0x3498db, 0x9b59b6, 0xff548d, 0xfffffe, 0x000001]
lang = ['日本語', 'English', '中文', '한국어']

class Configuration(commands.Cog):

	def __init__(self, bot):
		self.bot = bot
	
	@commands.command(brief='Set channel to send game notices')
	@commands.guild_only()
	@commands.has_permissions(manage_channels=True)
	@commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True, external_emojis=True, attach_files=True, manage_messages=True)
	async def setnotice(self,ctx):
		'''Use `setnotice` in selected channel'''

		def verify(m):
			return m.author.id == ctx.author.id

		print('Server attempt news channel set: %s %s' % (ctx.guild.id,ctx.guild.name))

		doc = db.collection(u'servers').document(u'{0}'.format(ctx.guild.id)).get()
		newslister = doc.to_dict().get('newschannel')

		if newslister == None:
			newslister = {}

		setchannel = ctx.channel.id

		strlang = '\n'.join([f'{i+1}: {lang[i]}' for i in range(len(lang))])
		embed = discord.Embed (
			title = 'Choose language',
			description = f'Input the number of the language.\n```{strlang}```',
			colour = discord.Colour(defaultcolour)
		)
		botmsg = await ctx.send(embed=embed)

		try:
			msginput = await self.bot.wait_for('message', check=verify, timeout=20.0)
		except asyncio.TimeoutError:
			print('timeout')
			return await botmsg.edit(embed=embederr('User took too long!'))

		if msginput.content.isdigit() and int(msginput.content) >= 1 and int(msginput.content) <= 7:
			noticelang = lang[int(msginput.content) - 1]
			await msginput.delete()
		else:
			await msginput.delete()
			return await botmsg.edit(embed=embederr('Invalid selection.'))

		if newslister.get(noticelang) != None:
			lister = newslister[noticelang]
		else:
			lister = None
		
		if setchannel == lister:
			return await botmsg.edit(embed=embederr('Combination exists.'))
		newslister[noticelang] = setchannel
		print(newslister)

		for i in [*newslister]:
			if self.bot.get_channel(newslister[i]) == None:
				del newslister[i]

		db.collection(u'servers').document(u'{0}'.format(ctx.guild.id)).update({ u'newschannel': newslister })

		donembed = discord.Embed (
			title = 'Success',
			color = discord.Colour.green(),
			description = 'Current notice channels',
			)
		for i in [*newslister]:
			channelnames = self.bot.get_channel(newslister[i]).mention
			donembed.add_field(name=i, value=channelnames, inline=False)
		return await botmsg.edit(embed=donembed)

	@commands.command(brief='Resets game notices channel')
	@commands.guild_only()
	@commands.has_permissions(manage_channels=True)
	@commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True, manage_messages=True)
	async def resetnotice(self,ctx):
		'''Use `resetnotice` in selected channel '''

		print('Server attempt news channel reset: %s %s' % (ctx.guild.id,ctx.guild.name))

		def verify(m):
			return m.author.id == ctx.author.id

		doc = db.collection(u'servers').document(u'{0}'.format(ctx.guild.id)).get()
		newslister = doc.to_dict().get('newschannel')

		if newslister == None or newslister == {}:
			return await ctx.send(embed=embederr('No notices channel in this server found.'))

		setchannel = ctx.channel.id

		embed = discord.Embed (
			title = 'Confirm action',
			description = 'Enter `yes` to confirm action, `no` to cancel action.',
			colour = discord.Colour(defaultcolour)
		)
		botmsg = await ctx.send(embed=embed)

		try:
			msginput = await self.bot.wait_for('message', check=verify, timeout=20.0)
		except asyncio.TimeoutError:
			print('timeout')
			return await botmsg.edit(embed=embederr('User took too long!'))

		if msginput.content == 'yes':
			await msginput.delete()
		else:
			await msginput.delete()
			return await botmsg.edit(embed=embederr('Command cancelled.'))

		for i in list(dict.fromkeys(newslister)):
			if self.bot.get_channel(newslister[i]) == None:
				del newslister[i]

			if newslister[i] == ctx.channel.id:
				del newslister[i]

		if newslister == {}:
			db.collection(u'servers').document(u'{0}'.format(ctx.guild.id)).update({ u'newschannel': firestore.DELETE_FIELD })
		else:
			db.collection(u'servers').document(u'{0}'.format(ctx.guild.id)).update({ u'newschannel': newslister })

		donembed = discord.Embed (
			title = 'Success',
			color = discord.Colour.green(),
			description = 'Current notice channels',
			)
		if newslister != {}:
			for i in [*newslister]:
				channelnames = self.bot.get_channel(newslister[i]).mention
				donembed.add_field(name=i, value=channelnames, inline=False)
		else:
			donembed.add_field(name='No channels configured.',value='Use setnotice <channel> to set one.', inline=False)
		return await botmsg.edit(embed=donembed)

	@commands.command(brief='Sets custom bot prefix within guild')
	@commands.guild_only()
	@commands.has_permissions(manage_channels=True)
	@commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True)
	async def setprefix(self,ctx, prefix):
		''' Set alt bot prefix by using `setprefix <prefix>`'''
		print('Server attempt prefix change: %s %s' % (ctx.guild.id,ctx.guild.name))
		
		db.collection(u'servers').document(u'{0}'.format(ctx.guild.id)).update({u'prefix': prefix})
		self.bot.guildprefixes[str(ctx.guild.id)] = prefix

		okembed = discord.Embed (
			title='Success',
			colour = discord.Colour.green(),
			description = f'Bot prefix changed to `{prefix}`.',
		)
		return await ctx.send(embed=okembed)

def setup(bot):
	bot.add_cog(Configuration(bot))