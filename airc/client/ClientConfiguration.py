from airc.Enums import IRCTimeout
from airc.dcc.DCCController import DCCController

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
			IRCTimeout.DCCAckResumeTimeoutSecs:							20,
			IRCTimeout.DCCPassiveConnectTimeoutSecs:					20,
		}
		self._autojoin_channels = set()
		self._handle_ctcp_version = False
		self._report_version = None
		self._handle_ctcp_time = False
		self._report_time_deviaton_secs = 0
		self._handle_ctcp_ping = False
		self._handle_dcc = False
		self._dcc_controller = None

	def timeout(self, key: IRCTimeout):
		return self._timeouts[key]

	def set_timeout(self, key: IRCTimeout, value: int | float):
		self._timeouts[key] = value

	@property
	def autojoin_channels(self):
		return iter(self._autojoin_channels)

	def add_autojoin_channel(self, channel: str):
		self._autojoin_channels.add(channel)

	@property
	def handle_ctcp_version(self):
		return self._handle_ctcp_version

	@handle_ctcp_version.setter
	def handle_ctcp_version(self, value: bool):
		self._handle_ctcp_version = value

	@property
	def version(self):
		return self._report_version

	@version.setter
	def version(self, value: str):
		self._handle_ctcp_version = True
		self._report_version = value

	@property
	def handle_ctcp_time(self):
		return self._handle_ctcp_time

	@handle_ctcp_time.setter
	def handle_ctcp_time(self, value: bool):
		self._handle_ctcp_time = value

	@property
	def time_deviation_secs(self):
		return self._report_time_deviation_secs

	@time_deviation_secs.setter
	def time_deviation_secs(self, value: int):
		self._handle_ctcp_time = True
		self._report_time_deviation_secs = value

	@property
	def handle_ctcp_ping(self):
		return self._handle_ctcp_ping

	@handle_ctcp_ping.setter
	def handle_ctcp_ping(self, value: bool):
		self._handle_ctcp_ping = value

	@property
	def handle_dcc(self):
		return self._handle_dcc

	@handle_dcc.setter
	def handle_dcc(self, value: bool):
		self._handle_dcc = value

	@property
	def dcc_controller(self):
		return self._dcc_controller

	@dcc_controller.setter
	def dcc_controller(self, value: DCCController):
		self.handle_dcc = True
		self._dcc_controller = value
