import re
import datetime
import ipaddress

from ..bbot_fixtures import *


@pytest.mark.asyncio
async def test_helpers(helpers, scan, bbot_scanner, bbot_config, bbot_httpserver):
    ### URL ###
    bad_urls = (
        "http://e.co/index.html",
        "http://e.co/u/1111/info",
        "http://e.co/u/2222/info",
        "http://e.co/u/3333/info",
        "http://e.co/u/4444/info",
        "http://e.co/u/5555/info",
    )
    new_urls = tuple(helpers.collapse_urls(bad_urls, threshold=4))
    assert len(new_urls) == 2
    new_urls = tuple(sorted([u.geturl() for u in helpers.collapse_urls(bad_urls, threshold=5)]))
    assert new_urls == bad_urls

    new_url = helpers.add_get_params("http://evilcorp.com/a?p=1&q=2", {"r": 3, "s": "asdf"}).geturl()
    query = dict(s.split("=") for s in new_url.split("?")[-1].split("&"))
    query = tuple(sorted(query.items(), key=lambda x: x[0]))
    assert query == (
        ("p", "1"),
        ("q", "2"),
        ("r", "3"),
        ("s", "asdf"),
    )
    assert tuple(sorted(helpers.get_get_params("http://evilcorp.com/a?p=1&q=2#frag").items())) == (
        ("p", ["1"]),
        ("q", ["2"]),
    )

    assert helpers.clean_url("http://evilcorp.com:80").geturl() == "http://evilcorp.com/"
    assert helpers.clean_url("http://evilcorp.com/asdf?a=asdf#frag").geturl() == "http://evilcorp.com/asdf"
    assert helpers.clean_url("http://evilcorp.com//asdf").geturl() == "http://evilcorp.com/asdf"

    assert helpers.url_depth("http://evilcorp.com/asdf/user/") == 2
    assert helpers.url_depth("http://evilcorp.com/asdf/user") == 2
    assert helpers.url_depth("http://evilcorp.com/asdf/") == 1
    assert helpers.url_depth("http://evilcorp.com/asdf") == 1
    assert helpers.url_depth("http://evilcorp.com/") == 0
    assert helpers.url_depth("http://evilcorp.com") == 0

    ### MISC ###
    assert helpers.is_domain("evilcorp.co.uk")
    assert not helpers.is_domain("www.evilcorp.co.uk")
    assert helpers.is_subdomain("www.evilcorp.co.uk")
    assert not helpers.is_subdomain("evilcorp.co.uk")
    assert helpers.is_url("http://evilcorp.co.uk/asdf?a=b&c=d#asdf")
    assert helpers.is_url("https://evilcorp.co.uk/asdf?a=b&c=d#asdf")
    assert helpers.is_uri("ftp://evilcorp.co.uk") == True
    assert helpers.is_uri("http://evilcorp.co.uk") == True
    assert helpers.is_uri("evilcorp.co.uk", return_scheme=True) == ""
    assert helpers.is_uri("ftp://evilcorp.co.uk", return_scheme=True) == "ftp"
    assert helpers.is_uri("FTP://evilcorp.co.uk", return_scheme=True) == "ftp"
    assert not helpers.is_url("https:/evilcorp.co.uk/asdf?a=b&c=d#asdf")
    assert not helpers.is_url("/evilcorp.co.uk/asdf?a=b&c=d#asdf")
    assert not helpers.is_url("ftp://evilcorp.co.uk")
    assert helpers.parent_domain("www.evilcorp.co.uk") == "evilcorp.co.uk"
    assert helpers.parent_domain("evilcorp.co.uk") == "evilcorp.co.uk"
    assert helpers.parent_domain("localhost") == "localhost"
    assert list(helpers.domain_parents("test.www.evilcorp.co.uk")) == ["www.evilcorp.co.uk", "evilcorp.co.uk"]
    assert list(helpers.domain_parents("www.evilcorp.co.uk", include_self=True)) == [
        "www.evilcorp.co.uk",
        "evilcorp.co.uk",
    ]
    assert list(helpers.domain_parents("evilcorp.co.uk", include_self=True)) == ["evilcorp.co.uk"]
    assert list(helpers.ip_network_parents("0.0.0.0/2")) == [
        ipaddress.ip_network("0.0.0.0/1"),
        ipaddress.ip_network("0.0.0.0/0"),
    ]
    assert list(helpers.ip_network_parents("0.0.0.0/1", include_self=True)) == [
        ipaddress.ip_network("0.0.0.0/1"),
        ipaddress.ip_network("0.0.0.0/0"),
    ]
    assert helpers.is_ip("127.0.0.1")
    assert not helpers.is_ip("127.0.0.0.1")

    assert helpers.domain_stem("evilcorp.co.uk") == "evilcorp"
    assert helpers.domain_stem("www.evilcorp.co.uk") == "www.evilcorp"

    assert helpers.host_in_host("www.evilcorp.com", "evilcorp.com") == True
    assert helpers.host_in_host("asdf.www.evilcorp.com", "evilcorp.com") == True
    assert helpers.host_in_host("evilcorp.com", "www.evilcorp.com") == False
    assert helpers.host_in_host("evilcorp.com", "evilcorp.com") == True
    assert helpers.host_in_host("evilcorp.com", "eevilcorp.com") == False
    assert helpers.host_in_host("eevilcorp.com", "evilcorp.com") == False
    assert helpers.host_in_host("evilcorp.com", "evilcorp") == False
    assert helpers.host_in_host("evilcorp", "evilcorp.com") == False
    assert helpers.host_in_host("evilcorp.com", "com") == True

    assert tuple(helpers.extract_emails("asdf@asdf.com\nT@t.Com&a=a@a.com__ b@b.com")) == (
        "asdf@asdf.com",
        "t@t.com",
        "a@a.com",
        "b@b.com",
    )

    assert helpers.split_host_port("https://evilcorp.co.uk") == ("evilcorp.co.uk", 443)
    assert helpers.split_host_port("http://evilcorp.co.uk:666") == ("evilcorp.co.uk", 666)
    assert helpers.split_host_port("evilcorp.co.uk:666") == ("evilcorp.co.uk", 666)
    assert helpers.split_host_port("evilcorp.co.uk") == ("evilcorp.co.uk", None)
    assert helpers.split_host_port("d://wat:wat") == ("wat", None)
    assert helpers.split_host_port("https://[dead::beef]:8338") == (ipaddress.ip_address("dead::beef"), 8338)
    extracted_words = helpers.extract_words("blacklanternsecurity")
    assert "black" in extracted_words
    # assert "blacklantern" in extracted_words
    # assert "lanternsecurity" in extracted_words
    # assert "blacklanternsecurity" in extracted_words
    assert "bls" in extracted_words

    choices = ["asdf.fdsa", "asdf.1234", "4321.5678"]
    best_match = helpers.closest_match("asdf.123a", choices)
    assert best_match == "asdf.1234"
    best_matches = helpers.closest_match("asdf.123a", choices, n=2)
    assert len(best_matches) == 2
    assert best_matches[0] == "asdf.1234"
    assert best_matches[1] == "asdf.fdsa"

    ipv4_netloc = helpers.make_netloc("192.168.1.1", 80)
    assert ipv4_netloc == "192.168.1.1:80"
    ipv6_netloc = helpers.make_netloc("dead::beef", "443")
    assert ipv6_netloc == "[dead::beef]:443"

    assert helpers.get_file_extension("https://evilcorp.com/evilcorp.com/test/asdf.TXT") == "txt"
    assert helpers.get_file_extension("/etc/conf/test.tar.gz") == "gz"
    assert helpers.get_file_extension("/etc/passwd") == ""

    assert helpers.tagify("HttP  -_Web  Title--  ") == "http-web-title"
    tagged_event = scan.make_event("127.0.0.1", source=scan.root_event, tags=["HttP  web -__- title  "])
    assert "http-web-title" in tagged_event.tags
    tagged_event.remove_tag("http-web-title")
    assert "http-web-title" not in tagged_event.tags
    tagged_event.add_tag("Another tag  ")
    assert "another-tag" in tagged_event.tags
    tagged_event.tags = ["Some other tag  "]
    assert isinstance(tagged_event._tags, set)
    assert "another-tag" not in tagged_event.tags
    assert "some-other-tag" in tagged_event.tags

    assert list(helpers.search_dict_by_key("asdf", {"asdf": "fdsa", 4: [{"asdf": 5}]})) == ["fdsa", 5]
    assert list(helpers.search_dict_by_key("asdf", {"wat": {"asdf": "fdsa"}})) == ["fdsa"]
    assert list(helpers.search_dict_by_key("asdf", [{"wat": {"nope": 1}}, {"wat": [{"asdf": "fdsa"}]}])) == ["fdsa"]
    assert not list(helpers.search_dict_by_key("asdf", [{"wat": {"nope": 1}}, {"wat": [{"fdsa": "asdf"}]}]))
    assert not list(helpers.search_dict_by_key("asdf", "asdf"))

    filtered_dict = helpers.filter_dict(
        {"modules": {"c99": {"api_key": "1234", "filterme": "asdf"}, "ipneighbor": {"test": "test"}}}, "api_key"
    )
    assert "api_key" in filtered_dict["modules"]["c99"]
    assert "filterme" not in filtered_dict["modules"]["c99"]
    assert "ipneighbor" not in filtered_dict["modules"]

    filtered_dict2 = helpers.filter_dict(
        {"modules": {"c99": {"api_key": "1234", "filterme": "asdf"}, "ipneighbor": {"test": "test"}}}, "c99"
    )
    assert "api_key" in filtered_dict2["modules"]["c99"]
    assert "filterme" in filtered_dict2["modules"]["c99"]
    assert "ipneighbor" not in filtered_dict2["modules"]

    filtered_dict3 = helpers.filter_dict(
        {"modules": {"c99": {"api_key": "1234", "filterme": "asdf"}, "ipneighbor": {"test": "test"}}},
        "key",
        fuzzy=True,
    )
    assert "api_key" in filtered_dict3["modules"]["c99"]
    assert "filterme" not in filtered_dict3["modules"]["c99"]
    assert "ipneighbor" not in filtered_dict3["modules"]

    filtered_dict4 = helpers.filter_dict(
        {"modules": {"secrets_db": {"api_key": "1234"}, "ipneighbor": {"secret": "test", "asdf": "1234"}}},
        "secret",
        fuzzy=True,
        exclude_keys="modules",
    )
    assert not "secrets_db" in filtered_dict4["modules"]
    assert "ipneighbor" in filtered_dict4["modules"]
    assert "secret" in filtered_dict4["modules"]["ipneighbor"]
    assert "asdf" not in filtered_dict4["modules"]["ipneighbor"]

    cleaned_dict = helpers.clean_dict(
        {"modules": {"c99": {"api_key": "1234", "filterme": "asdf"}, "ipneighbor": {"test": "test"}}}, "api_key"
    )
    assert "api_key" not in cleaned_dict["modules"]["c99"]
    assert "filterme" in cleaned_dict["modules"]["c99"]
    assert "ipneighbor" in cleaned_dict["modules"]

    cleaned_dict2 = helpers.clean_dict(
        {"modules": {"c99": {"api_key": "1234", "filterme": "asdf"}, "ipneighbor": {"test": "test"}}}, "c99"
    )
    assert "c99" not in cleaned_dict2["modules"]
    assert "ipneighbor" in cleaned_dict2["modules"]

    cleaned_dict3 = helpers.clean_dict(
        {"modules": {"c99": {"api_key": "1234", "filterme": "asdf"}, "ipneighbor": {"test": "test"}}},
        "key",
        fuzzy=True,
    )
    assert "api_key" not in cleaned_dict3["modules"]["c99"]
    assert "filterme" in cleaned_dict3["modules"]["c99"]
    assert "ipneighbor" in cleaned_dict3["modules"]

    cleaned_dict4 = helpers.clean_dict(
        {"modules": {"secrets_db": {"api_key": "1234"}, "ipneighbor": {"secret": "test", "asdf": "1234"}}},
        "secret",
        fuzzy=True,
        exclude_keys="modules",
    )
    assert "secrets_db" in cleaned_dict4["modules"]
    assert "ipneighbor" in cleaned_dict4["modules"]
    assert "secret" not in cleaned_dict4["modules"]["ipneighbor"]
    assert "asdf" in cleaned_dict4["modules"]["ipneighbor"]

    replaced = helpers.search_format_dict(
        {"asdf": [{"wat": {"here": "#{replaceme}!"}}, {500: True}]}, replaceme="asdf"
    )
    assert replaced["asdf"][1][500] == True
    assert replaced["asdf"][0]["wat"]["here"] == "asdf!"

    assert helpers.split_list([1, 2, 3, 4, 5]) == [[1, 2], [3, 4, 5]]
    assert list(helpers.grouper("ABCDEFG", 3)) == [["A", "B", "C"], ["D", "E", "F"], ["G"]]

    assert len(helpers.rand_string(3)) == 3
    assert len(helpers.rand_string(1)) == 1
    assert len(helpers.rand_string(0)) == 0
    assert type(helpers.rand_string(0)) == str

    test_file = Path(scan.config["home"]) / "testfile.asdf"
    test_file.touch()

    assert test_file.is_file()
    backup = helpers.backup_file(test_file)
    assert backup.name == "testfile.1.asdf"
    assert not test_file.exists()
    assert backup.is_file()
    test_file.touch()
    backup2 = helpers.backup_file(test_file)
    assert backup2.name == "testfile.1.asdf"
    assert not test_file.exists()
    assert backup2.is_file()
    older_backup = Path(scan.config["home"]) / "testfile.2.asdf"
    assert older_backup.is_file()
    older_backup.unlink()
    backup.unlink()

    with open(test_file, "w") as f:
        f.write("asdf\nfdsa")

    assert "asdf" in helpers.str_or_file(str(test_file))
    assert "nope" in helpers.str_or_file("nope")
    assert tuple(helpers.chain_lists([str(test_file), "nope"], try_files=True)) == ("asdf", "fdsa", "nope")
    assert test_file.is_file()

    with pytest.raises(DirectoryCreationError, match="Failed to create.*"):
        helpers.mkdir(test_file)

    helpers._rm_at_exit(test_file)
    assert not test_file.exists()

    timedelta = datetime.timedelta(hours=1, minutes=2, seconds=3)
    assert helpers.human_timedelta(timedelta) == "1 hour, 2 minutes, 3 seconds"
    timedelta = datetime.timedelta(hours=3, seconds=1)
    assert helpers.human_timedelta(timedelta) == "3 hours, 1 second"
    timedelta = datetime.timedelta(seconds=2)
    assert helpers.human_timedelta(timedelta) == "2 seconds"

    ### VALIDATORS ###
    # hosts
    assert helpers.validators.validate_host(" evilCorp.COM") == "evilcorp.com"
    assert helpers.validators.validate_host("LOCALHOST ") == "localhost"
    assert helpers.validators.validate_host(" 192.168.1.1") == "192.168.1.1"
    assert helpers.validators.validate_host(" Dead::c0dE ") == "dead::c0de"
    assert helpers.validators.soft_validate(" evilCorp.COM", "host") == True
    assert helpers.validators.soft_validate("!@#$", "host") == False
    with pytest.raises(ValueError):
        assert helpers.validators.validate_host("!@#$")
    # ports
    assert helpers.validators.validate_port(666) == 666
    assert helpers.validators.validate_port(666666) == 65535
    assert helpers.validators.soft_validate(666, "port") == True
    assert helpers.validators.soft_validate("!@#$", "port") == False
    with pytest.raises(ValueError):
        helpers.validators.validate_port("asdf")
    # urls
    assert helpers.validators.validate_url(" httP://evilcorP.com/asdf?a=b&c=d#e") == "http://evilcorp.com/asdf"
    assert (
        helpers.validators.validate_url_parsed(" httP://evilcorP.com/asdf?a=b&c=d#e").geturl()
        == "http://evilcorp.com/asdf"
    )
    assert helpers.validators.soft_validate(" httP://evilcorP.com/asdf?a=b&c=d#e", "url") == True
    assert helpers.validators.soft_validate("!@#$", "url") == False
    with pytest.raises(ValueError):
        helpers.validators.validate_url("!@#$")
    # severities
    assert helpers.validators.validate_severity(" iNfo") == "INFO"
    assert helpers.validators.soft_validate(" iNfo", "severity") == True
    assert helpers.validators.soft_validate("NOPE", "severity") == False
    with pytest.raises(ValueError):
        helpers.validators.validate_severity("NOPE")
    # emails
    assert helpers.validators.validate_email(" bOb@eViLcorp.COM") == "bob@evilcorp.com"
    assert helpers.validators.soft_validate(" bOb@eViLcorp.COM", "email") == True
    assert helpers.validators.soft_validate("!@#$", "email") == False
    with pytest.raises(ValueError):
        helpers.validators.validate_email("!@#$")

    assert type(helpers.make_date()) == str

    # punycode
    assert helpers.smart_encode_punycode("ドメイン.テスト") == "xn--eckwd4c7c.xn--zckzah"
    assert helpers.smart_decode_punycode("xn--eckwd4c7c.xn--zckzah") == "ドメイン.テスト"
    assert helpers.smart_encode_punycode("evilcorp.com") == "evilcorp.com"
    assert helpers.smart_decode_punycode("evilcorp.com") == "evilcorp.com"
    assert helpers.smart_encode_punycode("bob@ドメイン.テスト") == "bob@xn--eckwd4c7c.xn--zckzah"
    assert helpers.smart_decode_punycode("bob@xn--eckwd4c7c.xn--zckzah") == "bob@ドメイン.テスト"
    with pytest.raises(ValueError):
        helpers.smart_decode_punycode(b"asdf")
    with pytest.raises(ValueError):
        helpers.smart_encode_punycode(b"asdf")

    assert helpers.recursive_decode("Hello%20world%21") == "Hello world!"
    assert helpers.recursive_decode("Hello%20%5Cu041f%5Cu0440%5Cu0438%5Cu0432%5Cu0435%5Cu0442") == "Hello Привет"
    assert helpers.recursive_decode("%5Cu0020%5Cu041f%5Cu0440%5Cu0438%5Cu0432%5Cu0435%5Cu0442%5Cu0021") == " Привет!"
    assert helpers.recursive_decode("Hello%2520world%2521") == "Hello world!"
    assert (
        helpers.recursive_decode("Hello%255Cu0020%255Cu041f%255Cu0440%255Cu0438%255Cu0432%255Cu0435%255Cu0442")
        == "Hello Привет"
    )
    assert (
        helpers.recursive_decode("%255Cu0020%255Cu041f%255Cu0440%255Cu0438%255Cu0432%255Cu0435%255Cu0442%255Cu0021")
        == " Привет!"
    )
    assert (
        helpers.recursive_decode(r"Hello\\nWorld\\\tGreetings\\\\nMore\nText") == "Hello\nWorld\tGreetings\nMore\nText"
    )

    ### CACHE ###
    helpers.cache_put("string", "wat")
    helpers.cache_put("binary", b"wat")
    assert helpers.cache_get("string") == "wat"
    assert helpers.cache_get("binary") == "wat"
    assert helpers.cache_get("binary", text=False) == b"wat"
    cache_filename = helpers.cache_filename("string")
    (m, i, d, n, u, g, sz, atime, mtime, ctime) = os.stat(str(cache_filename))
    # change modified time to be 10 days in the past
    os.utime(str(cache_filename), times=(atime, mtime - (3600 * 24 * 10)))
    assert helpers.cache_get("string", cache_hrs=24 * 7) is None
    assert helpers.cache_get("string", cache_hrs=24 * 14) == "wat"

    cache_dict = helpers.CacheDict(max_size=10)
    cache_dict.put("1", 2)
    assert cache_dict["1"] == 2
    assert cache_dict.get("1") == 2
    assert len(cache_dict) == 1
    cache_dict["2"] = 3
    assert cache_dict["2"] == 3
    assert cache_dict.get("2") == 3
    assert len(cache_dict) == 2
    for i in range(20):
        cache_dict[str(i)] = i + 1
    assert len(cache_dict) == 10
    assert tuple(cache_dict) == tuple(hash(str(x)) for x in range(10, 20))

    test_file = Path(scan.config["home"]) / "testfile.asdf"
    with open(test_file, "w") as f:
        for i in range(100):
            f.write(f"{i}\n")
    assert len(list(open(test_file).readlines())) == 100
    assert (await helpers.wordlist(test_file)).is_file()
    truncated_file = await helpers.wordlist(test_file, lines=10)
    assert truncated_file.is_file()
    assert len(list(open(truncated_file).readlines())) == 10
    with pytest.raises(WordlistError):
        await helpers.wordlist("/tmp/a9pseoysadf/asdkgjaosidf")
    test_file.unlink()

    # misc DNS helpers
    assert helpers.is_ptr("wsc-11-22-33-44-wat.evilcorp.com") == True
    assert helpers.is_ptr("wsc-11-22-33-wat.evilcorp.com") == False
    assert helpers.is_ptr("11wat.evilcorp.com") == False

    ## NTLM
    testheader = "TlRMTVNTUAACAAAAHgAeADgAAAAVgorilwL+bvnVipUAAAAAAAAAAJgAmABWAAAACgBjRQAAAA9XAEkATgAtAFMANAAyAE4ATwBCAEQAVgBUAEsAOAACAB4AVwBJAE4ALQBTADQAMgBOAE8AQgBEAFYAVABLADgAAQAeAFcASQBOAC0AUwA0ADIATgBPAEIARABWAFQASwA4AAQAHgBXAEkATgAtAFMANAAyAE4ATwBCAEQAVgBUAEsAOAADAB4AVwBJAE4ALQBTADQAMgBOAE8AQgBEAFYAVABLADgABwAIAHUwOZlfoNgBAAAAAA=="
    decoded = helpers.ntlm.ntlmdecode(testheader)
    assert decoded["NetBIOS_Domain_Name"] == "WIN-S42NOBDVTK8"
    assert decoded["NetBIOS_Computer_Name"] == "WIN-S42NOBDVTK8"
    assert decoded["DNS_Domain_name"] == "WIN-S42NOBDVTK8"
    assert decoded["FQDN"] == "WIN-S42NOBDVTK8"
    assert decoded["Timestamp"] == b"u09\x99_\xa0\xd8\x01"
    with pytest.raises(NTLMError):
        helpers.ntlm.ntlmdecode("asdf")

    test_filesize = Path("/tmp/test_filesize")
    test_filesize.touch()
    assert test_filesize.is_file()
    assert helpers.filesize(test_filesize) == 0
    assert helpers.filesize("/tmp/glkasjdlgksadlkfsdf") == 0

    # memory stuff
    int(helpers.memory_status().available)
    int(helpers.swap_status().total)

    assert helpers.bytes_to_human(459819198709) == "428.24GB"
    assert helpers.human_to_bytes("428.24GB") == 459819198709

    scan1 = bbot_scanner(modules="ipneighbor")
    await scan1.load_modules()
    assert int(helpers.get_size(scan1.modules["ipneighbor"])) > 0


def test_word_cloud(helpers, bbot_config, bbot_scanner):
    number_mutations = helpers.word_cloud.get_number_mutations("base2_p013", n=5, padding=2)
    assert "base0_p013" in number_mutations
    assert "base7_p013" in number_mutations
    assert "base8_p013" not in number_mutations
    assert "base2_p008" in number_mutations
    assert "base2_p007" not in number_mutations
    assert "base2_p018" in number_mutations
    assert "base2_p0134" in number_mutations
    assert "base2_p0135" not in number_mutations

    permutations = helpers.word_cloud.mutations("_base", numbers=1)
    assert ("_base", "dev") in permutations
    assert ("dev", "_base") in permutations

    # saving and loading
    scan1 = bbot_scanner("127.0.0.1", config=bbot_config)
    word_cloud = scan1.helpers.word_cloud
    word_cloud.add_word("lantern")
    word_cloud.add_word("black")
    word_cloud.add_word("black")
    word_cloud.save()
    with open(word_cloud.default_filename) as f:
        word_cloud_content = [l.rstrip() for l in f.read().splitlines()]
    assert len(word_cloud_content) == 2
    assert "2\tblack" in word_cloud_content
    assert "1\tlantern" in word_cloud_content
    word_cloud.save(limit=1)
    with open(word_cloud.default_filename) as f:
        word_cloud_content = [l.rstrip() for l in f.read().splitlines()]
    assert len(word_cloud_content) == 1
    assert "2\tblack" in word_cloud_content
    assert "1\tlantern" not in word_cloud_content
    word_cloud.clear()
    with open(word_cloud.default_filename, "w") as f:
        f.write("plumbus\nrumbus")
    word_cloud.load()
    assert word_cloud["plumbus"] == 1
    assert word_cloud["rumbus"] == 1

    # mutators
    from bbot.core.helpers.wordcloud import DNSMutator

    m = DNSMutator()
    m.add_word("blacklantern-security")
    m.add_word("sec")
    m.add_word("sec2")
    m.add_word("black2")
    mutations = sorted(m.mutations("whitebasket"))
    assert mutations == sorted(
        [
            "basket",
            "basket-security",
            "basket2",
            "basketlantern-security",
            "blackbasket-security",
            "blacklantern-basket",
            "blacklantern-white",
            "blacklantern-whitebasket",
            "blackwhite-security",
            "blackwhitebasket-security",
            "white",
            "white-security",
            "white2",
            "whitebasket",
            "whitebasket-security",
            "whitebasket2",
            "whitebasketlantern-security",
            "whitelantern-security",
        ]
    )
    top_mutations = sorted(m.top_mutations().items(), key=lambda x: x[-1], reverse=True)
    assert top_mutations[:2] == [((None,), 3), ((None, "2"), 2)]


def test_queues(scan, helpers):
    from bbot.core.helpers.queueing import EventQueue

    module_priority_1 = helpers._make_dummy_module("one")
    module_priority_2 = helpers._make_dummy_module("two")
    module_priority_3 = helpers._make_dummy_module("three")
    module_priority_4 = helpers._make_dummy_module("four")
    module_priority_5 = helpers._make_dummy_module("five")
    module_priority_1._priority = 1
    module_priority_2._priority = 2
    module_priority_3._priority = 3
    module_priority_4._priority = 4
    module_priority_5._priority = 5
    event1 = module_priority_1.make_event("1.1.1.1", source=scan.root_event)
    event2 = module_priority_2.make_event("2.2.2.2", source=scan.root_event)
    event3 = module_priority_3.make_event("3.3.3.3", source=scan.root_event)
    event4 = module_priority_4.make_event("4.4.4.4", source=scan.root_event)
    event5 = module_priority_5.make_event("5.5.5.5", source=scan.root_event)

    event_queue = EventQueue()
    for e in [event1, event2, event3, event4, event5]:
        event_queue.put(e)

    assert event1 == event_queue._queues[1].get().event
    assert event2 == event_queue._queues[2].get().event
    assert event3 == event_queue._queues[3].get().event
    assert event4 == event_queue._queues[4].get().event
    assert event5 == event_queue._queues[5].get().event

    # insert each event 10000 times
    for i in range(10000):
        for e in [event1, event2, event3, event4, event5]:
            event_queue.put(e)

    # get 5000 events from queue and count how many of each there are
    stats = dict()
    for i in range(5000):
        e = event_queue.get()
        try:
            stats[e.id] += 1
        except KeyError:
            stats[e.id] = 1

    # make sure there's at least one of each event
    for e in [event1, event2, event3, event4, event5]:
        assert e.id in stats

    # make sure there are more of the higher-priority ones
    assert stats[event1.id] > stats[event2.id] > stats[event3.id] > stats[event4.id] > stats[event5.id]


def test_names(helpers):
    assert helpers.names == sorted(helpers.names)
    assert helpers.adjectives == sorted(helpers.adjectives)
