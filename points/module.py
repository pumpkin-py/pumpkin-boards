import datetime
import random
from typing import Union

import discord
from discord.ext import commands, tasks

import database.config
from core import utils, i18n

from .database import UserStats

_ = i18n.Translator("modules/fun").translate
config = database.config.Config.get()

class Points(commands.Cog):
    """Get points by having conversations"""

    def __init__(self, bot):
        self.bot = bot

        self.stats_message = {}
        self.stats_reaction = {}
        
        # This should be configurable
        self.limits_message = [15, 25]
        
        self.limits_reaction = [0, 5]
        
        self.timer_message = 60
        self.timer_reaction = 30
        
        self.board_limit = 10

        self.cleanup.start()

    ##
    ## Commands
    ##

    @commands.guild_only()
    @commands.group(name="points", aliases=["body"])
    async def points(self, ctx):
        """Get information about user points"""
        await utils.Discord.send_help(ctx)

    @points.command(name="get", aliases=["gde", "me", "stalk"])
    async def points_get(self, ctx, member: discord.Member = None):
        """Get user points"""
        if member is None:
            member = ctx.author

        result = UserStats.get_stats(ctx.guild.id, member.id)

        embed = utils.Discord.create_embed(
            author=ctx.author,
            title = config.prefix + ctx.command.qualified_name,
            description=_(
                ctx,
                (
                    "**{user}'s** points".format(user=utils.Text.sanitise(member.display_name))
                )
            )
        )
        points = getattr(result, "points", 0)
        message = ("**{points}** ({position}.)".format(points=points,position=UserStats.get_position(ctx.guild.id, points)))
        
        embed.set_thumbnail(url=member.display_avatar.replace(size=256).url)
        embed.add_field(
            name=_(ctx, ("Points and ranking")),
            value=_(ctx, message),
        )
        await ctx.send(embed=embed)
        await utils.Discord.delete_message(ctx.message)


    @points.command(name="leaderboard", aliases=["🏆"])
    async def points_leaderboard(self, ctx):
        """Points leaderboard"""
        embed = utils.Discord.create_embed(
            author=ctx.author,
            title=_(ctx, "Points ") + _(ctx, ("🏆")),
            description=_(ctx, "Score, descending")
        )
                
        users = UserStats.get_best(ctx.guild.id, "desc", self.board_limit, offset=0)
        value = self._getBoard(ctx.guild, ctx.author, users)
        
        embed.add_field(
            name=_(ctx, "Top {limit}".format(limit=self.board_limit)),
            value=value,
            inline=False,
        )

        # if the user is not present, add them to second field
        if ctx.author.id not in [u.user_id for u in users]:
            author = UserStats.get_stats(ctx.guild.id, ctx.author.id)

            embed.add_field(
                name=_(ctx, "Your score"),
                value="`{points:>8}` … {name}".format(
                    points=author.points, name="**" + utils.Text.sanitise(ctx.author.display_name) + "**"
                ),
                inline=False,
            )

        message = await ctx.send(embed=embed)
        await message.add_reaction("⏪")
        await message.add_reaction("◀")
        await message.add_reaction("▶")
        await utils.Discord.delete_message(ctx.message)

    @points.command(name="loserboard", aliases=["💩"])
    async def points_loserboard(self, ctx):
        """Points loserboard"""
        embed = utils.Discord.create_embed(
            author=ctx.author,
            title=_(ctx, "Points ") + _(ctx, ("💩")),
            description=_(ctx, "Score, ascending")
        )
        
        users = UserStats.get_best(ctx.guild.id, "asc", limit=self.board_limit, offset=0)
        value = self._getBoard(ctx.guild, ctx.author, users)
        
        embed.add_field(
            name=_(ctx, "Worst {limit}".format(limit=self.board_limit)),
            value=value,
            inline=False,
        )

        # if the user is not present, add them to second field
        if ctx.author.id not in [u.user_id for u in users]:
            author = repo_p.get(ctx.author.id)

            embed.add_field(
                name=_(ctx, "Your score"),
                value="`{points:>8}` … {name}".format(
                    points=author.points, name="**" + utils.Text.sanitise(ctx.author.display_name) + "**"
                ),
                inline=False,
            )

        message = await ctx.send(embed=embed)
        await message.add_reaction("⏪")
        await message.add_reaction("◀")
        await message.add_reaction("▶")
        await utils.Discord.delete_message(ctx.message)

    ##
    ## Listeners
    ##

    @commands.Cog.listener()
    async def on_message(self, message):
        """Add points on message"""
        if message.author.bot:
            return

        # Ignore DMs
        if not isinstance(message.channel, discord.TextChannel):
            return

        now = datetime.datetime.now()
        
        if not message.guild.id in self.stats_message:
            self.stats_message[message.guild.id] = {}

        if (
            str(message.author.id) in self.stats_message[message.guild.id]
            and (now - self.stats_message[message.guild.id][str(message.author.id)]).total_seconds()
            < self.timer_message
        ):
            return

        value = random.randint(self.limits_message[0], self.limits_message[1])
        self.stats_message[message.guild.id][str(message.author.id)] = now
        UserStats.increment(message.guild.id, message.author.id, value)


    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle board scrolling"""
        if user.bot:
            return

        if getattr(reaction.message, "guild", None) is None:
            return

        # add points
        now = datetime.datetime.now()
        
        guild_id = reaction.message.guild.id;
        
        
        if not guild_id in self.stats_reaction:
            self.stats_reaction[guild_id] = {}
        
        if (
            str(user.id) not in self.stats_reaction[guild_id]
            or (now - self.stats_reaction[guild_id][str(user.id)]).total_seconds() >= self.timer_reaction
        ):
            value = random.randint(self.limits_reaction[0], self.limits_reaction[1])
            self.stats_reaction[guild_id][str(user.id)] = now
            UserStats.increment(guild_id, user.id, value)

        if str(reaction) not in ("⏪", "◀", "▶"):
            return
            
        if len(reaction.message.embeds) != 1 \
        or type(reaction.message.embeds[0].title) != str \
        or not reaction.message.embeds[0].title.startswith(_(ctx, "Points ")):
            return

        embed = reaction.message.embeds[0]

        # get ordering
        if embed.title.endswith(_(ctx, "🏆")):
            order = "desc"
        else:
            order = "asc"

        # get current offset
        if ", " in embed.fields[0].name:
            offset = int(embed.fields[0].name.split(" ")[-1]) - 1
        else:
            offset = 0

        # get new offset
        if str(reaction) == "⏪":
            offset = 0
        elif str(reaction) == "◀":
            offset -= self.config.get("board")
        elif str(reaction) == "▶":
            offset += self.config.get("board")

        if offset < 0:
            return await utils.Discord.remove_reaction(reaction.message, reaction, user)

        users = repo_p.getUsers(order, limit=self.config.get("board"), offset=offset)
        value = self._getBoard(reaction.message.guild, user, users)
        if not value:
            # offset too big
            return await utils.Discord.remove_reaction(reaction.message, reaction, user)
    
        if order == "desc":
            table_name = _(ctx, "Best {limit}")
        else:
            table_name = _(ctx, "Worst {limit}")
            
        name = table_name.format(limit=self.board_limit)
    
        if offset:
            name += _(ctx, ", page {offset}".format(offset=offset + 1))

        embed.clear_fields()
        embed.add_field(name=name, value=value, inline=False)

        # if the user is not present, add them to second field
        if user.id not in [u.user_id for u in users]:
            author = UserStats.get_stats(guild_id, user.id)

            embed.add_field(
                name=_(ctx, "Your score"),
                value="`{points:>8}` … {name}".format(
                    points=author.points, name="**" + utils.Text.sanitise(user.display_name) + "**"
                ),
                inline=False,
            )

        await reaction.message.edit(embed=embed)
        await utils.Discord.remove_reaction(reaction.message, reaction, user)

    ##
    ## Helper functions
    ##

    def _getBoard(guild: discord.Guild, author: Union[discord.User, discord.Member], users: list, offset: int = 0) -> str:
        result = []
        template = "`{points:>8}` … {name}"
        for db_user in users:
            user = guild.get_member(db_user.user_id)
            if user and user.display_name:
                name = utils.Text.sanitise(user.display_name, limit=1900)
            else:
                name = self.text.get("unknown")

            if db_user.user_id == author.id:
                name = "**" + name + "**"

            result.append(template.format(points=db_user.points, name=name))
        return "\n".join(result)

    ##
    ## Tasks
    ##

    @tasks.loop(seconds=120.0)
    async def cleanup(self):
        for guild in self.stats_message.keys():
            delete = []
            for uid, time in self.stats_message[guild].items():
                if (datetime.datetime.now() - time).total_seconds() >= self.timer_message:
                    delete.append(uid)
            for uid in delete:
                self.stats_message[guild].pop(uid)
            
        for guild in self.stats_reaction.keys():
            delete = []
            for uid, time in self.stats_reaction[guild].items():
                if (datetime.datetime.now() - time).total_seconds() >= self.timer_reaction:
                    delete.append(uid)
                
            for uid in delete:
                self.stats_reaction[guild].pop(uid)
            

def setup(bot) -> None:
    bot.add_cog(Points(bot))
