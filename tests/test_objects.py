from datetime import date, datetime
import iso8601

from faunadb.objects import Event, FaunaTime, Page, Ref, Set
from faunadb._json import parse_json
from faunadb import query
from tests.helpers import FaunaTestCase

class ObjectsTest(FaunaTestCase):
  def setUp(self):
    super(ObjectsTest, self).setUp()
    self.ref = Ref("classes", "frogs", "123")
    self.json_ref = '{"@ref":"classes/frogs/123"}'

  def test_ref(self):
    self.assertJson(self.ref, self.json_ref)

    keys = Ref("keys")
    self.assertEqual(keys.to_class(), keys)
    self.assertRaises(ValueError, keys.id)

    ref = Ref(keys, "123")
    self.assertEqual(ref.to_class(), keys)
    self.assertEqual(ref.id(), "123")

  def test_set(self):
    index = Ref("indexes", "frogs_by_size")
    json_index = '{"@ref":"indexes/frogs_by_size"}'
    match = Set(query.match(self.ref, index))
    json_match = '{"@set":{"match":%s,"terms":%s}}' % (json_index, self.json_ref)
    self.assertJson(match, json_match)

  def test_event(self):
    event = Event(self.ref, 123, "create")
    event_json = '{"action":"create","resource":{"@ref":"classes/frogs/123"},"ts":123}'
    self.assertEqual(Event.from_raw(parse_json(event_json)), event)
    self.assertToJson(event, event_json)

  def test_page(self):
    assert Page.from_raw({"data": 1, "before": 2, "after": 3}) == Page(1, 2, 3)
    assert Page([1, 2, 3], 2, 3).map_data(lambda x: x + 1) == Page([2, 3, 4], 2, 3)

  def test_set_iterator(self):
    class_ref = self.client.post("classes", {"name": "gadgets"})["ref"]
    index_ref = self.client.post("indexes", {
      "name": "gadgets_by_n",
      "source": class_ref,
      "path": "data.n",
      "active": True
    })["ref"]

    def create(n):
      q = query.create(class_ref, query.quote({"data": {"n": n}}))
      return self.client.query(q)["ref"]

    a = create(0)
    create(1)
    b = create(0)

    gadgets_set = query.match(0, index_ref)

    self.assertListEqual(list(Page.set_iterator(self.client, gadgets_set, page_size=1)), [a, b])

    query_mapper = lambda a: query.select(['data', 'n'], query.get(a))
    query_mapped_iter = Page.set_iterator(self.client, gadgets_set, map_lambda=query_mapper)
    self.assertListEqual(list(query_mapped_iter), [0, 0])

    mapped_iter = Page.set_iterator(self.client, gadgets_set, mapper=lambda x: [x])
    self.assertListEqual(list(mapped_iter), [[a], [b]])

  def test_time_conversion(self):
    dt = datetime.now(iso8601.UTC)
    self.assertEqual(FaunaTime(dt).to_datetime(), dt)

    dt = datetime.fromtimestamp(0, iso8601.UTC)
    ft = FaunaTime(dt)
    self.assertEqual(ft, FaunaTime("1970-01-01T00:00:00Z"))
    self.assertEqual(ft.to_datetime(), dt)

  def test_time(self):
    test_ts = FaunaTime("1970-01-01T00:00:00.123456789Z")
    test_ts_json = '{"@ts":"1970-01-01T00:00:00.123456789Z"}'
    self.assertJson(test_ts, test_ts_json)

  def test_date(self):
    test_date = date(1970, 1, 1)
    test_date_json = '{"@date":"1970-01-01"}'
    self.assertJson(test_date, test_date_json)
