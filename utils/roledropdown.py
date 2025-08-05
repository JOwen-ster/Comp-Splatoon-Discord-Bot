import discord


class RoleSelect(discord.ui.Select):
    def __init__(self, assignable_roles):
        # Filter roles that can be assigned (not @everyone, not managed, not higher than bot)

        # Create options for the dropdown (max 25 options)
        options = []
        for role in assignable_roles[:25]:  # Discord api limit is 25 options per dropdown
            options.append(discord.SelectOption(
                label=role.name,
                value=str(role.id))
            )

        super().__init__(
            placeholder="Choose a role to assign (removes previous role)...",
            options=options,
            max_values=1  # Only allow selecting one role at a time
        )

        self.assignable_roles = {str(role.id): role for role in assignable_roles}
        self.all_assignable_roles = assignable_roles  # Keep reference to all roles in the list

    async def callback(self, interaction: discord.Interaction):
        # Get the member who used the dropdown
        member = interaction.user

        # Get the selected role (only one since max_values=1)
        selected_role = self.assignable_roles[self.values[0]]

        added_roles = []
        removed_roles = []
        errors = []

        try:
            # First, remove any existing roles from this role list that the user has
            roles_to_remove = [role for role in self.all_assignable_roles if role in member.roles]
            
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason="Exclusive role selection - removing previous roles")
                removed_roles.extend([role.name for role in roles_to_remove])

            # Then add the new selected role (if it wasn't already the user's role)
            if selected_role not in roles_to_remove:
                await member.add_roles(selected_role, reason="Exclusive role selection - adding new role")
                added_roles.append(selected_role.name)
            else:
                # If the user selected the same role they already had, just acknowledge it
                pass

        except discord.Forbidden:
            errors.append(f"Missing permissions for role management")
        except discord.HTTPException as e:
            errors.append(f"Failed to modify roles: {str(e)}")

        # Create response message
        response_parts = []

        if added_roles:
            response_parts.append(f"✅ **Added role:** {', '.join(added_roles)}")

        if removed_roles:
            response_parts.append(f"❌ **Removed roles:** {', '.join(removed_roles)}")

        if errors:
            response_parts.append(f"⚠️ **Errors:** {', '.join(errors)}")

        if not response_parts:
            if selected_role in member.roles:
                response_parts.append(f"You already have the {selected_role.name} role.")
            else:
                response_parts.append("No changes were made.")

        await interaction.response.send_message("\n".join(response_parts), ephemeral=True)


class RoleView(discord.ui.View):
    def __init__(self, roles):
        super().__init__(timeout=None)
        self.add_item(RoleSelect(assignable_roles=roles))
