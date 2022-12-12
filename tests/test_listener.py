import unittest
from unittest.mock import Mock, AsyncMock, patch
from app.listener import ListenerCog
from discord.ext import commands

class TestListenerCog(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = AsyncMock()
        self.listener_cog = ListenerCog(self.bot)

    @patch('builtins.print')
    async def test_on_ready(self, mocked_print):
        # Set up mock text channels
        mock_channel_1 = Mock()
        mock_channel_1.name = "bot-control"
        mock_channel_1.send = AsyncMock()
        mock_channel_2 = Mock()
        mock_channel_2.name = "general"
        mock_channel_2.send = AsyncMock()
        self.bot.guilds = [Mock(text_channels=[mock_channel_1, mock_channel_2])]

        # Call on_ready and verify that the expected messages were sent
        await self.listener_cog.on_ready()
        mock_channel_1.send.assert_called_with('Bot Activated..')
        mock_channel_2.send.assert_not_called()

        # Verify that the print statements were called
        self.assertTrue(mocked_print.called_with('Running!\nActive in {}\n Member Count : {}'.format(self.bot.guilds[0].name,
                                                                                     self.bot.guilds[0].member_count)))

