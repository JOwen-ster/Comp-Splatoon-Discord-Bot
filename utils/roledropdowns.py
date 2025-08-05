import discord
from utils.embeds import BotConfirmationEmbed


class RoleSelectPowers(discord.ui.Select):
    def __init__(self, region_key, bot=None):
        super().__init__(
            custom_id=f"role_select_{region_key}",
            placeholder="Choose a role to assign (removes previous role)...",
            options=[discord.SelectOption(label="Loading...", value="loading")],
            min_values=1,
            max_values=1
        )
        self.region_key = region_key
        self.bot = bot
        self.assignable_roles = {}
        self.all_assignable_roles = []

    def update_roles(self, role_list: list):
        self.assignable_roles = {str(role.id): role for role in role_list}
        self.all_assignable_roles = role_list

        options = []
        for role in role_list[:25]:
            options.append(discord.SelectOption(label=role.name, value=str(role.id)))
        self.options = options or [discord.SelectOption(label="No roles available", value="none")]

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # Load roles if needed (for persistent views after restart)
        if not self.all_assignable_roles and self.bot:
            role_cog = self.bot.get_cog('Roles')
            if role_cog and interaction.guild:
                filtered_roles = role_cog.filter_xp_roles(key=self.region_key, iterable=interaction.guild.roles)
                self.update_roles(filtered_roles)

        # Validate selection
        if not self.all_assignable_roles or self.values[0] in ["none", "loading"]:
            await interaction.followup.send("❌ No valid roles available.", ephemeral=True)
            return

        member = interaction.user
        selected_role = self.assignable_roles[self.values[0]]

        # Remove existing roles from this category
        roles_to_remove = [role for role in self.all_assignable_roles if role in member.roles]

        try:
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)

            if selected_role not in roles_to_remove:
                await member.add_roles(selected_role)
                await interaction.followup.send(embed=BotConfirmationEmbed(
                    description=f"✅ **Added role:** {selected_role.name}\n❌**Removed role:** {roles_to_remove[0].name}"),
                    ephemeral=True
                )
            else:
                await interaction.followup.send(embed=BotConfirmationEmbed(description=f"You already have the {selected_role.name} role."), ephemeral=True)

        except discord.Forbidden:
            await interaction.followup.send("❌ Missing permissions for role management", ephemeral=True)
        except discord.HTTPException:
            await interaction.followup.send("❌ Failed to modify roles", ephemeral=True)


class RoleViewPowers(discord.ui.View):
    def __init__(self, region_key, bot=None):
        super().__init__(timeout=None)
        self.add_item(RoleSelectPowers(region_key=region_key, bot=bot))

    def update_roles(self, new_roles: list):
        self.children[0].update_roles(new_roles)


class RoleSelectRanks(discord.ui.Select):
    def __init__(self, bot=None):
        super().__init__(
            custom_id="role_select_ranks",
            placeholder="Choose a role to assign (removes previous role)...",
            options=[discord.SelectOption(label="Loading...", value="loading")],
            min_values=1,
            max_values=1
        )
        self.bot = bot
        self.assignable_roles = {}
        self.all_assignable_roles = []

    def update_roles(self, role_list: list):
        self.assignable_roles = {str(role.id): role for role in role_list}
        self.all_assignable_roles = role_list

        options = []
        for role in role_list[:25]:
            options.append(discord.SelectOption(label=role.name, value=str(role.id)))
        self.options = options or [discord.SelectOption(label="No roles available", value="none")]

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # Load roles if needed (for persistent views after restart)
        if not self.all_assignable_roles and self.bot:
            role_cog = self.bot.get_cog('Roles')
            if role_cog and interaction.guild:
                filtered_roles = role_cog.filter_rank_roles(iterable=interaction.guild.roles)
                self.update_roles(filtered_roles)

        # Validate selection
        if not self.all_assignable_roles or self.values[0] in ["none", "loading"]:
            await interaction.followup.send("❌ No valid roles available.", ephemeral=True)
            return

        member = interaction.user
        selected_role = self.assignable_roles[self.values[0]]

        # Remove existing roles from this category
        roles_to_remove = [role for role in self.all_assignable_roles if role in member.roles]

        try:
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)

            if selected_role not in roles_to_remove:
                await member.add_roles(selected_role)
                if roles_to_remove:
                    await interaction.followup.send(embed=BotConfirmationEmbed(
                        description=f"✅ **Added role:** {selected_role.name}\n❌ **Removed role:** {roles_to_remove[0].name}"),
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(embed=BotConfirmationEmbed(
                        description=f"✅ **Added role:** {selected_role.name}"),
                        ephemeral=True
                    )
            else:
                await interaction.followup.send(embed=BotConfirmationEmbed(description=f"You already have the {selected_role.name} role."), ephemeral=True)

        except discord.Forbidden:
            await interaction.followup.send("❌ Missing permissions for role management", ephemeral=True)
        except discord.HTTPException:
            await interaction.followup.send("❌ Failed to modify roles", ephemeral=True)


class RoleViewRanks(discord.ui.View):
    def __init__(self, bot=None):
        super().__init__(timeout=None)
        self.add_item(RoleSelectRanks(bot=bot))

    def update_roles(self, new_roles: list):
        self.children[0].update_roles(new_roles)