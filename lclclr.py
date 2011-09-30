# coding: utf-8

import web
from web import form
import urllib2
import redis
import json
import Image
import ImageStat
import StringIO
import flickrapi
from flickrapi import shorturl
import time
import datetime
import twitter
import re
import scipy
import scipy.cluster
import scipy.misc

try:
    import api_keys_dev as api_keys
except ImportError:
    import api_keys

r = redis.Redis(host='localhost', port=6379, db=1)
hp_auth = '&client_id='+api_keys.HYPERPUBLIC_ID+'&client_secret='+api_keys.HYPERPUBLIC_SECRET
hp_url = 'https://api.hyperpublic.com'

render = web.template.render('/usr/share/nginx/lclclr/templates/')

urls = (
    '/hp/(.+)/(.+)', 'hp',
    '/fl/(.+)/(.+)', 'fl',
    '/tw/(.+)/(.+)', 'tw',
    '/', 'index',
)

app = web.application(urls, globals(), autoreload=False)

flickr = flickrapi.FlickrAPI(api_keys.FLICKR_ID)
twitter_api = twitter.Api()

class index:
    def GET(self):
        return render.index()

def rnd(num):
    return '%.4f' % float(num)

def inCache(key):
    return r.exists(key)

def fromCache(key):
    cache_ids = r.lrange(key, 0, -1)
    cache_dict = {}
    for id in cache_ids:
        cache_dict[id] = r.hmget(id, ['src', 'lat', 'long'])
    return cache_dict

def getFlickrImgDict(lat, long):
    key = 'fl:'+lat+','+long
    if inCache(key):
        return fromCache(key)
    else:
        week_ago = datetime.datetime.now() - datetime.timedelta(weeks=1)
        week_ago_timestamp = str(int(time.mktime(week_ago.timetuple())))
        #geocontext='2'
        fl_response = flickr.photos_search(lat=lat, lon=long, radius='1', min_taken_date=week_ago_timestamp, has_geo='1', per_page='5')
        imgdict = {}
        for photo in fl_response[0]:
            imgurl = 'http://farm2.static.flickr.com/'+photo.attrib['server']+'/'+photo.attrib['id']+'_'+photo.attrib['secret']+'_s.jpg'
            fl_geo_response = flickr.photos_geo_getLocation(photo_id=photo.attrib['id'])
            imgdict[str(photo.attrib['id'])] = imgurl, fl_geo_response[0][0].attrib['latitude'], fl_geo_response[0][0].attrib['longitude']
            r.lpush(key, photo.attrib['id'])
            r.hmset(photo.attrib['id'], {'src':imgurl, 'lat':fl_geo_response[0][0].attrib['latitude'], 'long':fl_geo_response[0][0].attrib['longitude']})
            #r.expire(photo.attrib['id'], 86400)
        return imgdict

class fl:
    def GET(self, lat, long):
        lat, long = rnd(lat), rnd(long)
        imgdict = getFlickrImgDict(lat, long)
        colordict, mean_color = getColors(imgdict, 'fl')
        retdict = {'colors':colordict, 'mean':mean_color}
        web.header('Content-Type', 'application/json')
        return json.dumps(retdict)

def getHyperpublicImgDict(lat, long):
    key = 'hp:'+lat+','+long
    if inCache(key):
        return fromCache(key)
    else:
        hp_req_url = '/api/v1/places?limit=5&with_photo=true&radius=1&lat='+lat+'&lon='+long
        hp_response = urllib2.urlopen(hp_url+hp_req_url+hp_auth)
        photos = json.loads(hp_response.read())
        imgdict = {}
        for item in photos:
            imgurl = None
            if item.get('image'): imgurl = item.get('image').get('src_thumb')
            if not imgurl: continue
            item_lat = rnd(item['locations'][0]['lat'])
            item_long = rnd(item['locations'][0]['lon'])
            imgdict[str(item['id'])] = imgurl, item_lat, item_long
            r.lpush(key, item['id'])
            r.hmset(item['id'], {'src':imgurl, 'lat':item_lat, 'long':item_long})
            #r.expire(item['id'], 86400)
        return imgdict

class hp:
    def GET(self, lat, long):
        lat, long = rnd(lat), rnd(long)
        imgdict = getHyperpublicImgDict(lat, long)
        colordict, mean_color = getColors(imgdict, 'hp')
        retdict = {'colors':colordict, 'mean':mean_color}
        web.header('Content-Type', 'application/json')
        return json.dumps(retdict)

def getTwitterImgDict(lat, long):
    key = 'tw:'+lat+','+long
    if inCache(key):
        return fromCache(key)
    else:
        nearby_tweets = twitter_api.GetSearch(term=u'twitpic.com', geocode=(lat, long, '5km'), per_page=10)
        imgdict = {}
        for t in nearby_tweets:
            twitpic_match = re.search(r'http://twitpic.com/(\S+)', t.text)
            if twitpic_match:
                t_id = twitpic_match.group(1)
                imgurl = 'http://twitpic.com/show/mini/'+t_id
            else:
                continue
            geo_match = re.search(r'\s*(-?\d{1,2}\.\d+),\s*(-?\d{1,3}\.\d+)\s*', t.location)
            if geo_match:
                item_lat = rnd(geo_match.group(1))
                item_long = rnd(geo_match.group(2))
            else:
                continue
            imgdict[str(t_id)] = imgurl, item_lat, item_long, t.location
            r.lpush(key, t_id)
            r.hmset(t_id, {'src':imgurl, 'lat':item_lat, 'long':item_long})
            #r.expire(t_id, 86400)
        return imgdict

class tw:
    def GET(self, lat, long):
        lat, long = rnd(lat), rnd(long)
        imgdict = getTwitterImgDict(lat, long)
        colordict, mean_color = getColors(imgdict, 'tw')
        retdict = {'colors':colordict, 'mean':mean_color}
        web.header('Content-Type', 'application/json')
        return json.dumps(retdict)

def getColors(urldict, url_type=None):
    means = {}
    n = len(urldict)
    if n == 0:
        return None, None
    r_tot, g_tot, b_tot = 0, 0, 0
    for id in urldict.keys():
        #means[id] = getImageMeans(urldict[id][0])
        means[id] = getDominantColor(urldict[id][0])
        r_tot += int(means[id][0])
        g_tot += int(means[id][1])
        b_tot += int(means[id][2])
        if url_type == 'fl':
            url = shorturl.url(id)
        elif url_type == 'hp':
            url = 'http://hyperpublic.com/places/'+id
        elif url_type == 'tw':
            url = 'http://twitpic.com/'+id
        else:
            url = urldict[id][0]
        means[id].append(url)
        means[id].append([urldict[id][1], urldict[id][2]])
    mean_color = int(r_tot/n), int(g_tot/n), int(b_tot/n)
    return means, mean_color

def getDominantColor(img_url):
    if r.exists(img_url):
        cache_result = r.hmget(img_url, ['r', 'g', 'b'])
        return cache_result
        
    NUM_CLUSTERS = 5
    im = Image.open(StringIO.StringIO(urllib2.urlopen(img_url).read()))
    img_arr = scipy.misc.fromimage(im)
    img_shape = img_arr.shape
    
    if len(img_shape) > 2:
        img_arr = img_arr.reshape(scipy.product(img_shape[:2]), img_shape[2])
    
    codes, _ = scipy.cluster.vq.kmeans(img_arr, NUM_CLUSTERS)
    
    original_codes = codes
    for low, hi in [(60, 200), (35, 230), (10, 250)]:
        codes = scipy.array([code for code in codes if not (all([c < low for c in code]) or all([c > hi for c in code]))])
        if not len(codes):
            codes = original_codes
        else:
            break

    vecs, _ = scipy.cluster.vq.vq(img_arr, codes)
    counts, bins = scipy.histogram(vecs, len(codes))

    index_max = scipy.argmax(counts)
    peak = codes[index_max]
    color = [int(c) for c in peak[:3]]
    r.hmset(img_url, {'r':color[0], 'g':color[1], 'b':color[2]})
    #r.expire(img_url, 86400)
    return color

def getImageMeans(img_url):
    if r.exists(img_url):
        cache_result = r.hmget(img_url, ['r', 'g', 'b'])
        return cache_result
    else:
        im = Image.open(StringIO.StringIO(urllib2.urlopen(img_url).read()))
        cr = [int(num) for num in ImageStat.Stat(im).mean[:3]]
        r.hmset(img_url, {'r':cr[0], 'g':cr[1], 'b':cr[2]})
        #r.expire(img_url, 86400)
        return cr

application = app.wsgifunc()

if __name__ == "__main__":
    print('Initialized.')
    #app.run()

