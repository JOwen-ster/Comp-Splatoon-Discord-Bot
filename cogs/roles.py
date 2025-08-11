import discord
from discord.ext import commands
from discord import app_commands
from cogs import extensions
import utils.roledropdowns as rdd
from utils.embeds import BotMessageEmbed, BotErrorEmbed, BotConfirmationEmbed
from utils.loggingsetup import getlog
from db.persistent_db import ViewType, fetch_view, insert_view, delete_view, fetch_all_views, print_all_views
import re


# CREATE CUSTOM ID USING GUILD ID
# MAKE COMMANDS WORK FOR MANY SERVERS
# TRYING TO USE THE COMMAND WHEN A VIEW OF THAT COMMAND IS ALREADY PRESENT SHOULD DELETE THAT ORIGINAL VIEW MESSAGE
# TAKE IT OUT OF THE SQLITE AND STORE THE GUILD_ID AND THE MESSAGE EMBED_ID TO JUMP TO THEN ACCESS THE VIEW OR INSTA DELETE THYE VIEW)
        # self.persistent_messages = {
        #     'jp': {},  # guild_id: message_id, ...
        #     'na': {},  # guild_id: message_id, ...
        #     'ranks': {}  # guild_id: message_id, ...
        # }
#CREATE THE VIEW IN THE CHANNEL WHERE THE COMMAND WAS USED
# CREATE AUTO DELETE LISTENER EVENT TO CHECK IF THE MESSAGE ID IS IN THE DICT IF IT IS THEN REMOVE IT FROM THE DICT ANID SQLITE
# CREATE A COMMAND THAT GIVES MESSAGE LINKS TO ALL VIEWS FOR THE CURRENT SERVER
# CHANGE THE REGION ATTRIBUTE TO IDENTIFIER AND USE IT IN THE CUSTOM custom_id=f"rs_{identifier}_{guild_id}"
# STORE EACH VIEW IN SQLITE. 1 TABLE FOR EACH TYPE OF VIEW SUCH AS NA JP RANKED PINGS. Store guild id and message id for that view
# Read through database when bot starts and check each message id in its corresponding guild to see if it exists.
#If the view doesnt exist then the view got deleted and you can drop that row for that view
# Add the views guild id and message id to db if a view command gets ran
# USE AIOSQLITE FOR ASYNC SQLITE

class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
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

                elif view_type == "ranked":
                    roles = self.filter_rank_roles(guild.roles)
                    view = rdd.RoleViewRanks(
                        guild_id=guild_id,
                        msg_id=message_id,
                        bot=self.bot,
                    )
                    view.update_roles(roles)
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

    @app_commands.command(name="jp-roles", description="Get a dropdown to assign/remove roles")
    async def role_dropdown_jp(self, interaction: discord.Interaction):
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
        old_view_data = await fetch_view(ViewType.JP, interaction.guild.id)
        if old_view_data:
            old_message_id = old_view_data[2]
            try:
                old_msg = await interaction.channel.fetch_message(old_message_id)
                await old_msg.delete()
            except discord.NotFound:
                pass

        # Prepare new view
        na_xp_roles = self.filter_xp_roles(
            key='jp',
            iterable=interaction.guild.roles,
            xp_min=2000,
            xp_max=2900
        )

        title_embed = BotMessageEmbed(
            title="Japan XP Roles",
            description="Select Your Takoroka Division Power"
        )

        post = await interaction.channel.send(embed=title_embed)
        print(post.id)

        view = rdd.RoleViewPowers(
            region_key='jp',
            guild_id=interaction.guild.id,
            msg_id=post.id,
            bot=self.bot
        )
        view.update_roles(na_xp_roles)

        # Update drodown with view
        await post.edit(embed=title_embed, view=view)

        # Store in DB
        await insert_view(
            ViewType.JP,
            interaction.guild.id,
            interaction.channel.id,
            post.id,
            self.bot
        )

        await interaction.followup.send(embed=BotConfirmationEmbed(description='✅ Sent New Dropdown!'))

    @app_commands.command(name="na-roles", description="Get a dropdown to assign/remove roles")
    async def role_dropdown_na(self, interaction: discord.Interaction):
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
        old_view_data = await fetch_view(ViewType.NA, interaction.guild.id)
        if old_view_data:
            old_message_id = old_view_data[2]
            try:
                old_msg = await interaction.channel.fetch_message(old_message_id)
                await old_msg.delete()
            except discord.NotFound:
                pass

        # Prepare new view
        na_xp_roles = self.filter_xp_roles(
            key='na',
            iterable=interaction.guild.roles,
            xp_min=2000,
            xp_max=2900
        )

        title_embed = BotMessageEmbed(
            title="Western XP Roles",
            description="Select Your Tentatek Division Power"
        )

        post = await interaction.channel.send(embed=title_embed)
        print(post.id)

        view = rdd.RoleViewPowers(
            region_key='na',
            guild_id=interaction.guild.id,
            msg_id=post.id,
            bot=self.bot
        )
        view.update_roles(na_xp_roles)

        # Update drodown with view
        await post.edit(embed=title_embed, view=view)

        # Store in DB
        await insert_view(
            ViewType.NA,
            interaction.guild.id,
            interaction.channel.id,
            post.id,
            self.bot
        )

        await interaction.followup.send(embed=BotConfirmationEmbed(description='✅ Sent New Dropdown!'))

    # @app_commands.command(name='ranked-roles', description='Get a dropdown of ranks to assign/remove roles')
    # async def ranked_dropdown(self, interaction: discord.Interaction):
    #     if interaction.user.id not in self.bot.whitelist:
    #         return

    #     if not interaction.guild.me.guild_permissions.manage_roles:
    #         await interaction.response.send_message(embed=BotErrorEmbed(
    #             description="❌ I don't have the `Manage Roles` permission!"),
    #             ephemeral=True
    #         )
    #         return

    #     rank_roles = self.filter_rank_roles(iterable=interaction.guild.roles)
    #     view = rdd.RoleViewRanks(bot=self.bot)
    #     view.update_roles(rank_roles)
        
    #     embed = BotMessageEmbed(title="Ranked Roles", description="Select Your Ranked Division")
    #     await interaction.response.send_message(embed=embed, view=view)

    # @app_commands.command(name='ping-roles', description='Get a drodown of pingable roles to assign/remove')
    # async def ping_dropdown(self, interaction: discord.Interaction, list_ids: str):
    #     # the list_ids param wil be a comma seperated list in the form of a string with discord role ids.
    #     embed = BotMessageEmbed(title="Pingable Roles", description="Select All Roles You Want Pings For")
    #     await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Roles(bot))
