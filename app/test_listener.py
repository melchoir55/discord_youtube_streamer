import unittest
from unittest.mock import patch, MagicMock
from app.listener import ListenerCog
import pytest


class TestListenerCog(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.bot = unittest.mock.Mock()
        self.listener_cog = ListenerCog(self.bot)

    @pytest.mark.asyncio
    async def test_on_ready(self):
        guild1 = unittest.mock.Mock()
        guild1.name = 'Guild 1'
        guild1.member_count = 5
        channel1 = unittest.mock.Mock()
        channel1.name = 'bot-control'
        guild1.text_channels = [channel1]
        guild2 = unittest.mock.Mock()
        guild2.name = 'Guild 2'
        guild2.member_count = 10
        self.bot.guilds = [guild1, guild2]

        # Call the on_ready function
        await self.listener_cog.on_ready()

        # # Verify that the print statements were called
        # self.assertTrue(self.listener_cog.print.called)
        # self.assertTrue(self.listener_cog.print.called_with('Running!'))
        # self.assertTrue(self.listener_cog.print.called_with('Active in Guild 1\n Member Count : 5'))
        # self.assertTrue(self.listener_cog.print.called_with('Active in Guild 2\n Member Count : 10'))

        # Verify that the channel.send method was called with the correct message
        self.assertTrue(channel1.send.called)
        self.assertTrue(channel1.send.called_with('Bot Activated..'))
