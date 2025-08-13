import discord
from utils.embeds import BotConfirmationEmbed


class RoleSelectPowers(discord.ui.Select):
    def __init__(self, region_key, guild_id, msg_id, bot=None):
        super().__init__(
            custom_id=f"rs_{region_key}_{guild_id}_{msg_id}",
            placeholder="Choose a role to assign (removes previous role)...",
            options=[discord.SelectOption(label="Loading...", value="loading")],
            min_values=1,
            max_values=1
        )
        self.region_key = region_key
        self.guild_id = guild_id
        self.msg_id = msg_id
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
        await interaction.response.defer(ephemeral=True)
        
        try:
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

            cmd_user = interaction.user
            selected_role = self.assignable_roles[self.values[0]]

            # Remove existing roles from this category
            roles_to_remove = [role for role in self.all_assignable_roles if role in cmd_user.roles]

            try:
                if roles_to_remove:
                    await cmd_user.remove_roles(*roles_to_remove)

                if selected_role not in roles_to_remove:
                    removed_roles_names = ", ".join(role.name for role in roles_to_remove) if roles_to_remove else "No Previous XP Role"
                    await cmd_user.add_roles(selected_role)
                    await interaction.followup.send(embed=BotConfirmationEmbed(
                        description=f"✅ **Added role:** {selected_role.name}\n❌**Removed role:** {removed_roles_names}"),
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(embed=BotConfirmationEmbed(description=f"You already have the {selected_role.name} role."), ephemeral=True)

            except discord.Forbidden:
                await interaction.followup.send("❌ Missing permissions for role management", ephemeral=True)
            except discord.HTTPException:
                await interaction.followup.send("❌ Failed to modify roles", ephemeral=True)
        except Exception as e:
            print(e)


class RoleViewPowers(discord.ui.View):
    def __init__(self, region_key, guild_id, msg_id, bot=None):
        super().__init__(timeout=None)
        self.add_item(RoleSelectPowers(region_key=region_key, guild_id=guild_id, msg_id=msg_id, bot=bot))

    def update_roles(self, new_roles: list):
        self.children[0].update_roles(new_roles)


class RoleSelectRanks(discord.ui.Select):
    def __init__(self, guild_id, msg_id, bot=None):
        super().__init__(
            custom_id=f"rs_ranks_{guild_id}_{msg_id}",
            placeholder="Choose a role to assign (removes previous role)...",
            options=[discord.SelectOption(label="Loading...", value="loading")],
            min_values=1,
            max_values=1
        )
        self.guild_id = guild_id
        self.msg_id = msg_id
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
        await interaction.response.defer(ephemeral=True)

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
    def __init__(self, guild_id, msg_id, bot=None):
        super().__init__(timeout=None)
        self.add_item(RoleSelectRanks(guild_id=guild_id, msg_id=msg_id, bot=bot))

    def update_roles(self, new_roles: list):
        self.children[0].update_roles(new_roles)

class RoleSelectPings(discord.ui.Select):
    def __init__(self, guild_id, msg_id, bot=None):
        super().__init__(
            custom_id=f"rs_ping_{guild_id}_{msg_id}",
            placeholder="Choose roles to assign/remove...",
            options=[discord.SelectOption(label="Loading...", value="loading")],
            min_values=1,
            max_values=1  # will update dynamically
        )
        self.guild_id = guild_id
        self.msg_id = msg_id
        self.bot = bot
        self.assignable_roles = {}
        self.all_assignable_roles = []

    def update_roles(self, role_list: list):
        self.assignable_roles = {str(role.id): role for role in role_list}
        self.all_assignable_roles = role_list

        if role_list:
            options = [
                discord.SelectOption(
                    label=role.name.strip() or f"Role {role.id}",
                    value=str(role.id)
                )
                for role in role_list[:25]
            ]
            self.options = options
            self.min_values = 1
            self.max_values = min(len(options), 25)  # max 25 options selectable
        else:
            self.options = [discord.SelectOption(label="No roles available", value="none")]
            self.min_values = 1
            self.max_values = 1

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # Load roles if needed
        if not self.all_assignable_roles and self.bot:
            role_cog = self.bot.get_cog('Roles')
            if role_cog and interaction.guild:
                filtered_roles = role_cog.filter_ping_roles(iterable=interaction.guild.roles)
                self.update_roles(filtered_roles)

        # Validate selection
        if not self.all_assignable_roles or any(val in ["none", "loading"] for val in self.values):
            await interaction.followup.send("❌ No valid roles available.", ephemeral=True)
            return

        member = interaction.user
        selected_roles = [self.assignable_roles[val] for val in self.values if val in self.assignable_roles]

        if not selected_roles:
            await interaction.followup.send("❌ No valid roles selected.", ephemeral=True)
            return

        # Separate roles to add and roles to remove (toggle behavior)
        roles_to_remove = [role for role in selected_roles if role in member.roles]
        roles_to_add = [role for role in selected_roles if role not in member.roles]

        try:
            # Remove roles the user already has
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)
            # Add roles the user doesn't have
            if roles_to_add:
                await member.add_roles(*roles_to_add)

            # Build confirmation message
            description_parts = []
            if roles_to_add:
                added_names = ", ".join(r.name for r in roles_to_add)
                description_parts.append(f"✅ Added role(s): {added_names}")
            if roles_to_remove:
                removed_names = ", ".join(r.name for r in roles_to_remove)
                description_parts.append(f"❌ Removed role(s): {removed_names}")

            if description_parts:
                await interaction.followup.send(
                    embed=BotConfirmationEmbed(description="\n".join(description_parts)),
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    embed=BotConfirmationEmbed(description="No changes were made to your roles."),
                    ephemeral=True
                )

        except discord.Forbidden:
            await interaction.followup.send("❌ Missing permissions for role management.", ephemeral=True)
        except discord.HTTPException:
            await interaction.followup.send("❌ Failed to modify roles.", ephemeral=True)


class RoleViewPings(discord.ui.View):
    def __init__(self, guild_id, msg_id, bot=None):
        super().__init__(timeout=None)
        self.add_item(RoleSelectPings(guild_id=guild_id, msg_id=msg_id, bot=bot))

    def update_roles(self, new_roles: list):
        self.children[0].update_roles(new_roles)
