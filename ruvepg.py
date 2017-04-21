import sys
from datetime import datetime, date, timedelta
import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom


BASE_URL = 'https://muninn.ruv.is/files/xml/{channel}/{date_from}/{date_to}/'


class EPG:
    def __init__(self):
        self.root = ET.Element('tv')

    def add_channel(self, channel_id, lang, name):
        channel = ET.SubElement(self.root, 'channel')
        channel.set('id', channel_id)

        display_name = ET.SubElement(channel, 'display-name')
        display_name.set('lang', lang)
        display_name.text = name

    def add_programme(self, start, stop, channel, lang, programme_title):
        programme = ET.SubElement(self.root, 'programme')
        programme.set('start', start)
        programme.set('stop', stop)
        programme.set('channel', channel)

        title = ET.SubElement(programme, 'title')
        title.set('lang', lang)
        title.text = programme_title

    def to_xml(self):
        stringified = ET.tostring(self.root, 'utf-8')
        reparsed = minidom.parseString(stringified)
        return reparsed.toprettyxml(indent='  ')


class Event:
    DATE_FORMAT = '%Y%m%d%H%M%S +00:00'
    def __init__(self, event):
        self.event = event
        self.title = event.find('title').text
        self.start_datetime = datetime.strptime(self.event.get('start-time'), '%Y-%m-%d %H:%M:%S')
        dur = datetime.strptime(self.event.get('duration'), '%H:%M:%S')
        self.duration = timedelta(hours=dur.hour, minutes=dur.minute, seconds=dur.second)
        self.stop_datetime = self.start_datetime + self.duration

        self.start = self.start_datetime.strftime(self.DATE_FORMAT)
        self.stop = self.stop_datetime.strftime(self.DATE_FORMAT)

    def contains(self, e2):
        return self.start_datetime <= e2.start_datetime and self.stop_datetime >= e2.stop_datetime


def main(outfile):
    epg = EPG()
    epg.add_channel('ruv', 'is', 'Rúv')

    today = date.today()
    week = timedelta(days=7)

    date_from = str(today)
    date_to = str(today + week)

    url = BASE_URL.format(channel='ruv', date_from=date_from, date_to=date_to)
    response = requests.get(url)
    response.raise_for_status()
    root = ET.fromstring(response.text)
    event_elements = root.findall('.//event')
    events = [Event(e) for e in event_elements]

    for event in events:
        for subevent in events:
            if event.contains(subevent) and event != subevent:
                # We don't want parent events in our XML, such as KrakkaRúv
                break
        else:
            epg.add_programme(event.start, event.stop, 'ruv', 'is', event.title)

    with open(outfile, 'w') as f:
        f.write(epg.to_xml())


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: {} output.xml'.format(sys.argv[0]), file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
