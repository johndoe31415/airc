# airc
[![Build Status](https://github.com/johndoe31415/airc/actions/workflows/CI.yml/badge.svg)](https://github.com/johndoe31415/airc/actions/workflows/CI.yml)

airc is a pure Python3-based asynchronous IRC client (using asyncio) that
supports receiving DCC file transfers as well as anonymization of identity. For
example, it contains a list of commonly used DCC VERSION responses and their
respective frequencies and can connect to an IRC server randomly selecting one
of them (while maintaining the correct ratio, i.e, common IRC clients will be
chosen more commonly). It also will generate nicknames automatically that
"look" right.

## Dependencies
airc requires Python 3.10 or above.

## License
GNU GPL-3.
