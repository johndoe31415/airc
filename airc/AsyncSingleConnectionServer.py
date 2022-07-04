import asyncio

class AsyncSingleConnectionServer():
	def __init__(self, host: str | None, port: int, close_callback = None):
		self._host = host
		self._port = port
		self._close_callback = close_callback
		self._future = asyncio.Future()
		self._server = None

	@property
	def host(self):
		return self._host

	@property
	def port(self):
		return self._port

	def __accept_callback(self, reader, writer):
		future.set_result((reader, writer))

	async def start(self):
		self._server = await asyncio.start_server(accept_callback, host, port, backlog = 1, reuse_address = True, reuse_port = True)

	def __aenter__(self):
		return self

	def __aexit__(self, *exception):
		self._server.close()
		if self._close_callback is not None:
			self._close_callback(self)
