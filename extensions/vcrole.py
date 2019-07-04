import discord
import logging

from discord.ext import commands
from gsbot import GSBot


CONFIGPATH = 'config/vcrole.json'
logger = logging.getLogger('gsbot.vcrole')


class VCRole(commands.Cog):
    def __init__(self, bot: GSBot):
        self.bot = bot
        self.config = bot.load_config(CONFIGPATH)

    @commands.group()
    async def vcrole(self, ctx):
        # TODO: リンクしたVCと役職のリストを表示
        pass

    @vcrole.command(name='list')
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
    async def add_vcrole(self, ctx, vc: discord.VoiceChannel, role: discord.Role):
        # TODO: VCと役職の紐付けを追加する
        settings = self.config.get(str(vc.id))
        if settings is None:
            settings = list()

            data = dict()
            data['role_id'] = role.id
            data['guild_id'] = role.guild.id

            settings.append(data)
        else:
            data = dict()
            data['role_id'] = role.id
            data['guild_id'] = role.guild.id

            settings.append(data)

        self.config[str(vc.id)] = settings
        self.bot.save_config(CONFIGPATH, self.config)

    @vcrole.command(name='remove')
    async def remove_vcrole(self, ctx, vc: discord.VoiceChannel, index: int):
        # TODO: VCと役職の紐付けを削除する
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
        if before.channel is None:
            self.check_and_add_roles()

        elif after.channel is not None:
            self.check_and_remove_roles()
            self.check_and_add_roles()

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

    async def check_and_remove_roles(
        self, member: discord.Member, channel: discord.VoiceChannel
    ):
        setting = self.config.get(str(channel.id))

        if setting is None:
            return


def setup(bot):
    bot.add_cog(VCRole(bot))
