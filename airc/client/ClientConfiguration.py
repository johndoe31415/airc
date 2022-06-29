from airc.Enums import IRCTimeout

class ClientConfiguration():
	def __init__(self):
		self._timeouts = {
			IRCTimeout.RegistrationTimeoutSecs:							10,
			IRCTimeout.ReconnectTimeAfterNicknameExhaustionSecs:		60,
			IRCTimeout.ReconnectTimeAfterConnectionErrorSecs:			5,
			IRCTimeout.ReconnectTimeAfterSeveredConnectionSecs:			15,
			IRCTimeout.ReconnectTimeAfterServerParseExceptionSecs:		10,
			IRCTimeout.ReconnectTimeAfterTLSErrorSecs:					10,
			IRCTimeout.JoinChannelTimeoutSecs:							20,
			IRCTimeout.RejoinChannelTimeSecs:							10,
		}
		self._autojoin_channels = set()
		self._handle_ctcp_version = False
		self._report_version = None

	def timeout(self, key: IRCTimeout):
		return self._timeouts[key]

	def set_timeout(self, key: IRCTimeout, value: int | float):
		self._timeouts[key] = value

	@property
	def version(self):
		return self._report_version

	@version.setter
	def version(self, value: str):
		self._handle_ctcp_version = True
		self._report_version = value

	@property
	def handle_ctcp_version(self):
		return self._handle_ctcp_version

	@version.setter
	def handle_ctcp_version(self, value: bool):
		self._handle_ctcp_version = value

	@property
	def autojoin_channels(self):
		return iter(self._autojoin_channels)

	def add_autojoin_channel(self, channel: str):
		self._autojoin_channels.add(channel)
