import json
from pathlib import Path
import sys
import tempfile
import unittest
import threading
import fcntl
from unittest.mock import patch
from html.parser import HTMLParser
from urllib.parse import urlparse, unquote

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from store import Store,utc_now
from render import render,page_name


class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.scripts=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=="a" and "href" in attrs:self.links.append(attrs["href"])
        if tag=="script":self.scripts.append(attrs)


class RenderTests(unittest.TestCase):
    def test_latest_eval_uses_actual_instant_not_offset_string_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with Store(root/"db.sqlite") as store:
                store.record("capability",{"id":"x","kind":"skill","name":"Example","description":"test","source_path":str(root/"SKILL.md"),"revision":"current","discovered_at":utc_now()},producer="collector")
                for ident,stamp,result in [("older","2026-10-26T12:00:00+02:00","pass"),("newer","2026-10-26T11:00:00Z","fail")]:
                    store.record("eval",{"id":ident,"suite_id":"suite","capability_id":"x","occurred_at":stamp,"outcome":result,"source_path":str(root/"report.md"),"source_ref":ident,"revision":"current"},producer="eval-runner")
                render(store,root/"view")
                overview=(root/"view/index.html").read_text()
                self.assertIn("FAIL · current source revision",overview)
                self.assertNotIn("PASS · current source revision",overview)

    def test_older_concurrent_render_cannot_replace_a_newer_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);db=root/"db.sqlite";view=root/"view"
            cap={"id":"x","kind":"skill","name":"OLD","description":"old state","source_path":str(root/"SKILL.md"),"revision":"old","discovered_at":utc_now()}
            with Store(db) as store:store.record("capability",cap,producer="collector")
            old_waiting=threading.Event();release=threading.Event();new_started=threading.Event();failures=[]
            import render as module
            replace=module.os.replace
            def controlled_replace(source,target):
                if threading.current_thread().name=="old-view":
                    old_waiting.set()
                    if not release.wait(5):raise TimeoutError("old render not released")
                return replace(source,target)
            def worker(new=False):
                try:
                    with Store(db) as store:
                        if new:new_started.set()
                        render(store,view)
                except Exception as error:failures.append(error)
            with patch.object(module.os,"replace",side_effect=controlled_replace):
                old=threading.Thread(target=worker,name="old-view");old.start()
                self.assertTrue(old_waiting.wait(5))
                try:
                    # The old publisher must own the lock across snapshot and publish.
                    with (view/".render.lock").open("a") as lock:
                        with self.assertRaises(BlockingIOError):fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                    with Store(db) as store:store.record("capability",dict(cap,name="NEW",revision="new"),producer="collector")
                    new=threading.Thread(target=worker,args=(True,),name="new-view");new.start()
                    self.assertTrue(new_started.wait(5))
                finally:release.set()
                old.join(5);new.join(5)
            self.assertFalse(failures,failures)
            self.assertFalse(old.is_alive());self.assertFalse(new.is_alive())
            self.assertIn(">NEW</a>",(view/"index.html").read_text())
            self.assertNotIn(">OLD</a>",(view/"index.html").read_text())

    def test_escape_static_links_snapshot_and_revision_truth(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/"SKILL.md";source.write_text("original")
            with Store(root/"data/db.sqlite") as store:
                store.record("capability",{"id":"cap-x","kind":"skill","name":"<script>bad</script>","description":"<img src=x onerror=alert(1)>","source_path":str(source),"revision":"changed","discovered_at":utc_now()},producer="collector")
                store.record("eval",{"id":"eval-x","suite_id":"suite","capability_id":"cap-x","occurred_at":"2026-01-01","outcome":"pass","source_path":str(source),"source_ref":"case-1","revision":"old"},producer="eval-runner")
                first=render(store,root/"view")
                first_detail=Path(first["snapshot"])/"skills"/page_name("cap-x")
                content=first_detail.read_text()
                self.assertIn("different revision",content)
                self.assertIn("&lt;script&gt;bad&lt;/script&gt;",content)
                for file in (root/"view").rglob("*.html"):
                    parser=Links();parser.feed(file.read_text());self.assertFalse(parser.scripts)
                    for link in parser.links:
                        uri=urlparse(link)
                        if uri.scheme=="file":self.assertTrue(Path(unquote(uri.path)).is_file())
                        elif not uri.scheme and uri.path:self.assertTrue((file.parent/unquote(uri.path)).exists(),(file,link))
                        else:self.assertEqual(uri.scheme,"")
                second=render(store,root/"view")
                self.assertNotEqual(first["snapshot"],second["snapshot"])
                self.assertTrue(first_detail.exists())
                self.assertIn(Path(second["snapshot"]).name,(root/"view/index.html").read_text())
                self.assertEqual(source.read_text(),"original")


if __name__=="__main__":unittest.main()
