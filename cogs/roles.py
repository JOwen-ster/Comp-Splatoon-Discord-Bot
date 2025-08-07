import discord
from discord.ext import commands
from discord import app_commands
from cogs import extensions
import utils.roledropdowns as rdd
from utils.embeds import BotMessageEmbed, BotErrorEmbed
from utils.loggingsetup import getlog
import re

# MAKE COMMANDS WORK FOR MANY SERVERS
# CREATE CUSTOM ID USING GUILD ID
# TRYING TO USE THE COMMAND WHEN A VIEW OF THAT COMMAND IS ALREADY PRESENT SHOULD DELETE THAT ORIGINAL VIEW MESSAGE
#TAKE IT OUT OF THE DICTIONARY (OR SQLITE) (STORE THE GUILD ID AND THE MESSAGE ID TO INSTA DELETE OR ACCESS THE VIEW)
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
        # Dont do this anymore, FIX IT
        # TODO: Add the view dynamically when its created not at load time, call add_view when using a view creation command
        # then pass in its guild id to use in the custom id
        self.bot.add_view(rdd.RoleViewPowers(region_key='jp', bot=self.bot))
        self.bot.add_view(rdd.RoleViewPowers(region_key='na', bot=self.bot))
        self.bot.add_view(rdd.RoleViewRanks(bot=self.bot))

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.cog_counter += 1
        getlog().info(F'{__name__} ready ({self.bot.cog_counter}/{len(extensions)})')

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
        if interaction.user.id not in self.bot.whitelist:
            return

        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message(embed=BotErrorEmbed(
                description="❌ I don't have the `Manage Roles` permission!"),
                ephemeral=True
            )
            return

        jp_xp_roles = self.filter_xp_roles(key='jp', iterable=interaction.guild.roles, xp_min=2000, xp_max=2900)
        view = rdd.RoleViewPowers(region_key='jp', bot=self.bot)
        view.update_roles(jp_xp_roles)
        
        embed = BotMessageEmbed(title="Japan XP Roles", description="Select Your Takoroka Division Power")
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="na-roles", description="Get a dropdown to assign/remove roles")
    async def role_dropdown_na(self, interaction: discord.Interaction):
        if interaction.user.id not in self.bot.whitelist:
            return

        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message(embed=BotErrorEmbed(
                description="❌ I don't have the `Manage Roles` permission!"),
                ephemeral=True
            )
            return

        na_xp_roles = self.filter_xp_roles(key='na', iterable=interaction.guild.roles, xp_min=2000, xp_max=2900)
        view = rdd.RoleViewPowers(region_key='na', bot=self.bot)
        view.update_roles(na_xp_roles)
        
        embed = BotMessageEmbed(title="Western XP Roles", description="Select Your Tentatek Division Power")
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name='ranked-roles', description='Get a dropdown of ranks to assign/remove roles')
    async def ranked_dropdown(self, interaction: discord.Interaction):
        if interaction.user.id not in self.bot.whitelist:
            return

        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message(embed=BotErrorEmbed(
                description="❌ I don't have the `Manage Roles` permission!"),
                ephemeral=True
            )
            return

        rank_roles = self.filter_rank_roles(iterable=interaction.guild.roles)
        view = rdd.RoleViewRanks(bot=self.bot)
        view.update_roles(rank_roles)
        
        embed = BotMessageEmbed(title="Ranked Roles", description="Select Your Ranked Division")
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name='ping-roles', description='Get a drodown of pingable roles to assign/remove')
    async def ping_dropdown(self, interaction: discord.Interaction, list_ids: str):
        # the list_ids param wil be a comma seperated list in the form of a string with discord role ids.
        embed = BotMessageEmbed(title="Pingable Roles", description="Select All Roles You Want Pings For")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Roles(bot))
