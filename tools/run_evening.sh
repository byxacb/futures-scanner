#!/bin/bash
cd /Users/bianyawen/Desktop/期货
/usr/bin/python3 -m tools.briefing.evening --symbols rb,m,au,IF,sc 2>> daily/cron.err
