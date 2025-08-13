import discord
from discord.ext import commands
from discord import app_commands
from cogs import extensions
import utils.roledropdowns as rdd
from utils.embeds import BotMessageEmbed, BotErrorEmbed, BotConfirmationEmbed
from utils.loggingsetup import getlog
from db.persistent_db import ViewType, fetch_view, insert_view, delete_view, fetch_all_views, print_all_views
import re


class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.loop.create_task(self.restore_views())

    async def restore_views(self):
        # USE CHANNEL ID AND GUILD ID INSTEAD OF ITERATING THROUGH CHANNELS AND GUILDS TO CHECK IF A VIEW WAS DELETED WHEN THE BOT WAS OFFLINE.
        await self.bot.wait_until_ready()
        getlog().info("Loading persisted views from database...")

        rows = await fetch_all_views()  # returns (guild_id, channel_id, view_type, message_id)

        # MAYBE USE FETCH_ INSTEAD OF GET_ FOR REAL TIME API CALLs
        for guild_id, channel_id, view_type, message_id in rows:
            getlog().debug(f"Attempting to restore: guild={guild_id}, channel={channel_id}, type={view_type}, message={message_id}")

            # Get guild
            guild = self.bot.get_guild(guild_id)
            if not guild:
                getlog().warning(f"Guild {guild_id} not found. Removing this view from DB.")
                await delete_view(message_id, guild_id)
                continue

            # Get channel
            channel = guild.get_channel(channel_id)
            if not channel:
                getlog().warning(f"Channel {channel_id} not found in guild {guild_id}. Removing this view from DB.")
                await delete_view(message_id, guild_id)
                continue

            # Get message
            try:
                message = await channel.fetch_message(message_id)
            except discord.NotFound:
                getlog().warning(f"Message {message_id} not found in channel {channel_id} (guild {guild_id}). Removing this view from DB.")
                await delete_view(message_id, guild_id)
                continue
            except discord.Forbidden:
                getlog().warning(f"No permission to access channel {channel_id} in guild {guild_id}. Skipping restoration.")
                continue
            except discord.HTTPException as e:
                getlog().error(f"HTTP error while fetching message {message_id} in guild {guild_id}: {e}")
                continue

            # Restore correct view
            try:
                if view_type == "na":
                    roles = self.filter_xp_roles(
                        key='na',
                        iterable=guild.roles,
                        xp_min=2000,
                        xp_max=2900
                    )
                    view = rdd.RoleViewPowers(
                        region_key='na',
                        guild_id=guild_id,
                        msg_id=message_id,
                        bot=self.bot
                    )
                    view.update_roles(roles)
                    await message.edit(view=view)

                elif view_type == "jp":
                    roles = self.filter_xp_roles(
                        key='jp',
                        iterable=guild.roles,
                        xp_min=2000,
                        xp_max=2900
                    )
                    view = rdd.RoleViewPowers(
                        region_key='na',
                        guild_id=guild_id,
                        msg_id=message_id,
                        bot=self.bot
                    )
                    view.update_roles(roles)
                    await message.edit(view=view)

                elif view_type == "rank":
                    roles = self.filter_rank_roles(guild.roles)
                    view = rdd.RoleViewRanks(
                        guild_id=guild_id,
                        msg_id=message_id,
                        bot=self.bot,
                    )
                    view.update_roles(roles)
                    await message.edit(view=view)

                elif view_type == 'ping':
                    ping_roles = self.filter_ping_roles(guild.roles)
                    view = rdd.RoleViewPings(
                        guild_id=guild_id,
                        msg_id=message_id,
                        bot=self.bot,
                    )
                    view.update_roles(ping_roles)
                    await message.edit(view=view)

                else:
                    getlog().warning(f"Unknown view type '{view_type}' in guild {guild_id}. Skipping.")
                    continue

                getlog().info(f"Successfully restored {view_type} view in guild {guild_id} (message {message_id}).")

            except Exception as e:
                getlog().error(f"Failed to restore view {view_type} in guild {guild_id}: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.cog_counter += 1
        getlog().info(F'{__name__} ready ({self.bot.cog_counter}/{len(extensions)})')

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if not message.guild:
            return
        has_embed = len(message.embeds) > 0
        has_view = hasattr(message, "components") and len(message.components) > 0
        if has_embed and has_view:
            await delete_view(message.id, message.guild.id)

    def filter_xp_roles(self, key: str, iterable, xp_min: int, xp_max: int):
        filtered_roles = []
        for role in iterable:
            regex = re.search(r'(\d+)', role.name)
            current_xp = int(regex.group(1)) if regex else 0
            if xp_min <= current_xp <= xp_max and "xp" in role.name.lower() and key in role.name.lower():
                filtered_roles.append(role)
        return filtered_roles

    def filter_rank_roles(self, iterable):
        return [role for role in iterable if 'rank' in role.name.lower()]

    def filter_ping_roles(self, iterable):
        return [role for role in iterable if ('ping' in role.name.lower() or 'pings' in role.name.lower())]

    async def send_power_dropdown(
        self,
        interaction: discord.Interaction,
        view_type: ViewType,
        region_key: str,
        xp_min: int,
        xp_max: int,
        embed_title: str,
        embed_description: str
    ):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id not in self.bot.whitelist:
            return

        if not interaction.guild.me.guild_permissions.manage_roles or not interaction.guild.me.guild_permissions.administrator:
            await interaction.followup.send(
                embed=BotErrorEmbed(description="❌ I don't have the `Manage Roles` permission!"),
                ephemeral=True
            )
            return

        # Delete old view if it exists
        old_view_data = await fetch_view(view_type, interaction.guild.id)
        if old_view_data:
            old_channel = await interaction.guild.get_channel(old_view_data[3])
            old_message_id = old_view_data[4]
            try:
                old_msg = await old_channel.fetch_message(old_message_id)
                await old_msg.delete()
            except discord.NotFound:
                pass

        # Prepare new roles
        xp_roles = self.filter_xp_roles(
            key=region_key,
            iterable=interaction.guild.roles,
            xp_min=xp_min,
            xp_max=xp_max
        )

        # Create embed
        title_embed = BotMessageEmbed(
            title=embed_title,
            description=embed_description
        )

        # Send message
        post = await interaction.channel.send(embed=title_embed)
        print(post.id)

        # Create and attach view
        view = rdd.RoleViewPowers(
            region_key=region_key,
            guild_id=post.guild.id,
            msg_id=post.id,
            bot=self.bot
        )
        view.update_roles(xp_roles)
        await post.edit(view=view)

        # Store in DB
        await insert_view(
            view_type,
            interaction.guild.id,
            interaction.channel.id,
            post.id,
            self.bot
        )

        await interaction.followup.send(embed=BotConfirmationEmbed(description='✅ Sent New Dropdown!'))

    @app_commands.command(name="jp-roles", description="Get a dropdown to assign/remove roles")
    async def role_dropdown_jp(self, interaction: discord.Interaction):
        await self.send_power_dropdown(
            interaction=interaction,
            view_type=ViewType.JP,
            region_key='jp',
            xp_min=2000,
            xp_max=2900,
            embed_title="Japan XP Roles",
            embed_description="Select Your Takoroka Division Power"
        )

    @app_commands.command(name="na-roles", description="Get a dropdown to assign/remove roles")
    async def role_dropdown_na(self, interaction: discord.Interaction):
        await self.send_power_dropdown(
            interaction=interaction,
            view_type=ViewType.NA,
            region_key='na',
            xp_min=2000,
            xp_max=2900,
            embed_title="Western XP Roles",
            embed_description="Select Your Tentatek Division Power"
        )

    @app_commands.command(name='ranked-roles', description='Get a dropdown of ranks to assign/remove roles')
    async def ranked_dropdown(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id not in self.bot.whitelist:
            return

        if not interaction.guild.me.guild_permissions.manage_roles or not interaction.guild.me.guild_permissions.administrator:
            await interaction.followup.send(
                embed=BotErrorEmbed(description="❌ I don't have the `Manage Roles` permission!"),
                ephemeral=True
            )
            return

        # Delete old view if it exists
        old_view_data = await fetch_view(ViewType.RANK, interaction.guild.id)
        if old_view_data:
            old_channel = await interaction.guild.get_channel(old_view_data[3])
            old_message_id = old_view_data[4]
            try:
                old_msg = await old_channel.fetch_message(old_message_id)
                await old_msg.delete()
            except discord.NotFound:
                pass

        # Prepare new roles
        rank_roles = self.filter_rank_roles(interaction.guild.roles)

        # Create embed
        rank_title_embed = BotMessageEmbed(
            title='Ranked Roles',
            description='Select Your Most Recent Rank'
        )

        # Send message
        post = await interaction.channel.send(embed=rank_title_embed)
        print(post.id)

        view = rdd.RoleViewRanks(
            guild_id=post.guild.id,
            msg_id=post.id,
            bot=self.bot
        )
        view.update_roles(rank_roles)
        await post.edit(view=view)

        # Store in DB
        await insert_view(
            view_type=ViewType.RANK,
            guild_id=post.guild.id,
            channel_id=post.channel.id,
            message_id=post.id,
            bot=self.bot
        )

        await interaction.followup.send(embed=BotConfirmationEmbed(description='✅ Sent New Dropdown!'))

    @app_commands.command(name='ping-roles', description='Get a drodown of pingable roles to assign/remove')
    async def ping_dropdown(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id not in self.bot.whitelist:
            return

        if not interaction.guild.me.guild_permissions.manage_roles or not interaction.guild.me.guild_permissions.administrator:
            await interaction.followup.send(
                embed=BotErrorEmbed(description="❌ I don't have the `Manage Roles` permission!"),
                ephemeral=True
            )
            return

        # Delete old view if it exists
        old_view_data = await fetch_view(ViewType.PING, interaction.guild.id)
        if old_view_data:
            old_channel = await interaction.guild.get_channel(old_view_data[3])
            old_message_id = old_view_data[4]
            try:
                old_msg = await old_channel.fetch_message(old_message_id)
                await old_msg.delete()
            except discord.NotFound:
                pass

        ping_roles = self.filter_ping_roles(interaction.guild.roles)
        print('DEBUG'*100)
        print(ping_roles)

        ping_title_embed = BotMessageEmbed(title="Pingable Roles", description="Select All Roles You Want Pings For")

        post = await interaction.channel.send(embed=ping_title_embed)
        print(post.id)

        ping_view = rdd.RoleViewPings(
            guild_id=interaction.guild.id,
            msg_id=post.id,
            bot=self.bot
        )
        ping_view.update_roles(ping_roles)
        await post.edit(view=ping_view)

        # Store in DB
        await insert_view(
            ViewType.PING,
            post.guild.id,
            post.channel.id,
            post.id,
            self.bot
        )

        await interaction.followup.send(embed=BotConfirmationEmbed(description='✅ Sent New Dropdown!'))

async def setup(bot):
    await bot.add_cog(Roles(bot))
