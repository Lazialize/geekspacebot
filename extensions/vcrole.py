import discord
import logging

from discord.ext import commands
from gsbot import GSBot


CONFIGPATH = 'config/vcrole.json'
logger = logging.getLogger('gsbot.vcrole')


def check_executor_is_authorized_user(ctx):
    return ctx.author.id in [195816057926057994, 319226423623548928]


class VCRole(commands.Cog):
    def __init__(self, bot: GSBot):
        self.bot = bot
        self.config = bot.load_config(CONFIGPATH)

    @commands.group()
    async def vcrole(self, ctx):
        # TODO: リンクしたVCと役職のリストを表示
        pass

    @vcrole.command(name='list')
    @commands.check(check_executor_is_authorized_user)
    async def list_vcrole(self, ctx, vc: discord.VoiceChannel):
        settings = self.config.get(str(vc.id))

        if settings is None:
            await ctx.send('指定のボイスチャンネルにリンクされている役職は存在しません。')
            return

        embeds = list()
        embed = discord.Embed()
        count = 1
        for data in settings:
            guild = self.bot.get_guild(data['guild_id'])
            role = guild.get_role(data['role_id'])

            embed.add_field(
                name=str(count),
                value='Guild: {0}\nRole: {1}'.format(guild.name, role.name),
                inline=False,
            )

            count += 1

            # フィールドの数が20個になったら、新しいEmbedを作成する。
            if count % 20 == 0:
                embeds.append(embed)
                embed = discord.Embed()
        else:
            embeds.append(embed)

        for embed in embeds:
            await ctx.send(embed=embed)

    @vcrole.command(name='add')
    @commands.check(check_executor_is_authorized_user)
    async def add_vcrole(
        self, ctx, vc_guild_id: int, vc_id: int, role_guild_id: int, role_id: int
    ):
        vc_guild = self.bot.get_guild(vc_guild_id)

        if vc_guild is None:
            logger.warning(
                'Failed to get guild by vc_guild_id: {0}'.format(vc_guild_id)
            )
            return

        voice_channel = vc_guild.get_channel(vc_id)

        if isinstance(
            voice_channel, (type(None), discord.TextChannel, discord.DMChannel)
        ):
            logger.warning('Failed to get voice channel by vc_id: {0}'.format(vc_id))
            return

        role_guild = self.bot.get_guild(role_guild_id)

        if role_guild is None:
            logger.warning(
                'Failed to get guild by role_guild_id: {0}'.format(role_guild_id)
            )
            return

        role = role_guild.get_role(role_id)

        if role is None:
            logger.warning('Failed to get role by role_id: {0}'.format(role_id))
            return

        settings = self.config.get(str(vc_id))
        if settings is None:
            settings = list()

            data = dict()
            data['role_id'] = role.id
            data['guild_id'] = role_guild_id

            settings.append(data)
        else:
            data = dict()
            data['role_id'] = role.id
            data['guild_id'] = role.guild.id

            settings.append(data)

        self.config[str(vc_id)] = settings
        self.bot.save_config(CONFIGPATH, self.config)

    @vcrole.command(name='remove')
    @commands.check(check_executor_is_authorized_user)
    async def remove_vcrole(self, ctx, vc: discord.VoiceChannel, index: int):
        settings = self.config.get(str(vc.id))

        if settings is None:
            await ctx.send('指定のボイスチャンネルには役職が設定されていません。')
            return

        try:
            settings.pop(index - 1)
        except IndexError:
            await ctx.send('指定されたインデックスは範囲を超えています。')
            return

        self.config[str(vc.id)] = settings
        self.bot.save_config(CONFIGPATH, self.config)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        # VCへの接続・切断以外を破棄
        if before.channel == after.channel:
            return
        if before.channel is None:
            await self.check_and_add_roles(member, after.channel)
            return
        elif after.channel is None:
            await self.check_and_remove_roles(member, before.channel)
            return

        await self.check_and_remove_roles(member, before.channel)
        await self.check_and_add_roles(member, after.channel)

    # HACK: ネストが深すぎる。リファクタリングできればするべきである。
    @commands.Cog.listener()
    async def on_ready(self):
        for k, v in self.config.items():
            channel = self.bot.get_channel(int(k))

            for member in channel.members:
                self.check_and_add_roles(member, channel)

            for setting in v:
                guild = self.bot.get_guild(setting['guild_id'])
                role = guild.get_role(setting['role_id'])

                for member in role.members:
                    if member.voice is None:
                        continue

                    if member.voice.channel == channel:
                        continue

                    self.check_and_remove_roles(member, channel)

    # HACK: check_and_remove_rolesと被る部分が多い。名称も不明瞭。要リファクタリング。
    async def check_and_add_roles(
        self, member: discord.Member, channel: discord.VoiceChannel
    ):
        settings = self.config.get(str(channel.id))

        if settings is None:
            return

        for data in settings:
            guild = self.bot.get_guild(data['guild_id'])
            if guild is None:
                logger.warning('Guild is not found. ID: {0}'.format(data['guild_id']))
                continue

            role = guild.get_role(data['role_id'])
            if role is None:
                logger.warning('Role is not found. ID: {0}'.format(data['role_id']))
                continue

            target_member = guild.get_member(member.id)
            if target_member is None:
                logger.info('Member is not joined to Guild. ID: {0}'.format(member.id))
            await target_member.add_roles(role)

    # HACK: check_and_add_rolesと被る部分が多い。名称も不明瞭。要リファクタリング。
    async def check_and_remove_roles(
        self, member: discord.Member, channel: discord.VoiceChannel
    ):
        settings = self.config.get(str(channel.id))

        if settings is None:
            return

        for data in settings:
            guild = self.bot.get_guild(data['guild_id'])

            if guild is None:
                logger.warning('Guild is not found. ID: {0}'.format(data['guild_id']))
                continue

            role = guild.get_role(data['role_id'])
            if role is None:
                logger.warning('Role is not found. ID: {0}'.format(data['role_id']))
                continue

            target_member = guild.get_member(member.id)
            if target_member is None:
                logger.info('Member is not joined to Guild. ID: {0}'.format(member.id))
            await target_member.remove_roles(role)


def setup(bot):
    bot.add_cog(VCRole(bot))
