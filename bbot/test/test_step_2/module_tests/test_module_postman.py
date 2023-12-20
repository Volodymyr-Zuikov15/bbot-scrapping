from .base import ModuleTestBase


class TestPostman(ModuleTestBase):
    config_overrides = {
        "omit_event_types": [],
        "scope_report_distance": 1,
    }

    async def setup_before_prep(self, module_test):
        module_test.httpx_mock.add_response(
            url="https://www.postman.com/_api/ws/proxy",
            json={
                "data": [
                    {
                        "score": 499.22498,
                        "normalizedScore": 8.43312276976538,
                        "document": {
                            "isPublisherVerified": False,
                            "publisherType": "user",
                            "curatedInList": [],
                            "publisherId": "28329861",
                            "publisherHandle": "",
                            "publisherLogo": "",
                            "isPublic": True,
                            "customHostName": "",
                            "id": "28329861-28329861-f6ef-4f23-9f3a-8431f3567ac1",
                            "workspaces": [
                                {
                                    "visibilityStatus": "public",
                                    "name": "SpilledSecrets",
                                    "id": "afa061be-9cb0-4520-9d4d-fe63361daf0f",
                                    "slug": "spilledsecrets",
                                }
                            ],
                            "collectionForkLabel": "",
                            "method": "POST",
                            "entityType": "request",
                            "url": "www.example.com/index",
                            "isBlacklisted": False,
                            "warehouse__updated_at_collection": "2023-12-11 02:00:00",
                            "isPrivateNetworkEntity": False,
                            "warehouse__updated_at_request": "2023-12-11 02:00:00",
                            "publisherName": "NA",
                            "name": "A test post request",
                            "privateNetworkMeta": "",
                            "privateNetworkFolders": [],
                            "documentType": "request",
                            "collection": {
                                "id": "28129865-d9f8833b-3dd2-4b07-9634-1831206d5205",
                                "name": "Secret Collection",
                                "tags": [],
                                "forkCount": 0,
                                "watcherCount": 0,
                                "views": 31,
                                "apiId": "",
                                "apiName": "",
                            },
                        },
                    },
                ],
            },
        )
        module_test.httpx_mock.add_response(
            url="https://www.postman.com/_api/workspace/afa061be-9cb0-4520-9d4d-fe63361daf0f",
            json={
                "model_id": "afa061be-9cb0-4520-9d4d-fe63361daf0f",
                "meta": {"model": "workspace", "action": "find"},
                "data": {
                    "id": "afa061be-9cb0-4520-9d4d-fe63361daf0f",
                    "name": "SpilledSecrets",
                    "description": "A Mock workspace environment filled with fake secrets to act as a testing ground for secret scanners",
                    "summary": "A Public workspace with mock secrets",
                    "createdBy": "28329861",
                    "updatedBy": "28329861",
                    "team": "28329861",
                    "createdAt": "2023-12-13T19:12:21.000Z",
                    "updatedAt": "2023-12-13T19:15:07.000Z",
                    "visibilityStatus": "public",
                    "profileInfo": {
                        "slug": "spilledsecrets",
                        "profileType": "team",
                        "profileId": "28329861",
                        "publicHandle": "https://www.postman.com/lunar-pizza-28329861",
                        "publicImageURL": "https://res.cloudinary.com/postman/image/upload/t_team_logo/v1/team/default-L4",
                        "publicName": "lunar-pizza-28329861",
                        "isVerified": False,
                    },
                    "user": "28329861",
                    "type": "team",
                    "dependencies": {
                        "collections": ["28129865-d9f8833b-3dd2-4b07-9634-1831206d5205"],
                        "environments": ["28129865-fa7edca0-2df6-4187-9805-11845912f567"],
                        "globals": ["28735eff-5ecd-43e6-8473-387f160f220f"],
                    },
                    "members": {"users": {"28129865": {"id": "28129865"}}},
                },
            },
        )
        module_test.httpx_mock.add_response(
            url="https://www.postman.com/_api/list/collection?workspace=afa061be-9cb0-4520-9d4d-fe63361daf0f",
            json={
                "data": [
                    {
                        "id": "28129865-d9f8833b-3dd2-4b07-9634-1831206d5205",
                        "name": "Secret Collection",
                        "folders_order": ["d6dd1092-94d4-462c-be48-4e3cad3b8612"],
                        "order": ["67c9db4c-d0ed-461c-86d2-9a8c5a5de896"],
                        "attributes": {
                            "permissions": {
                                "userCanUpdate": False,
                                "userCanDelete": False,
                                "userCanShare": False,
                                "userCanCreateMock": False,
                                "userCanCreateMonitor": False,
                                "anybodyCanView": True,
                                "teamCanView": True,
                            },
                            "fork": None,
                            "parent": {"type": "workspace", "id": "afa061be-9cb0-4520-9d4d-fe63361daf0f"},
                            "flags": {"isArchived": False, "isFavorite": False},
                        },
                        "folders": [
                            {
                                "id": "28129865-d6dd1092-94d4-462c-be48-4e3cad3b8612",
                                "name": "Nested folder",
                                "folder": None,
                                "collection": "28129865-d9f8833b-3dd2-4b07-9634-1831206d5205",
                                "folders_order": ["73a999c1-4246-4805-91bd-0232cc75958a"],
                                "order": ["3aa78b71-2c4f-4299-94df-287ed1036409"],
                                "folders": [
                                    {
                                        "id": "28129865-73a999c1-4246-4805-91bd-0232cc75958a",
                                        "name": "Another Nested Folder",
                                        "folder": "28129865-d6dd1092-94d4-462c-be48-4e3cad3b8612",
                                        "collection": "28129865-d9f8833b-3dd2-4b07-9634-1831206d5205",
                                        "folders_order": [],
                                        "order": ["987c8ac8-bfa9-4bab-ade9-88ccf0597862"],
                                        "folders": [],
                                        "requests": [
                                            {
                                                "id": "28129865-987c8ac8-bfa9-4bab-ade9-88ccf0597862",
                                                "name": "Delete User",
                                                "method": "DELETE",
                                                "collection": "28129865-d9f8833b-3dd2-4b07-9634-1831206d5205",
                                                "folder": "28129865-73a999c1-4246-4805-91bd-0232cc75958a",
                                                "responses_order": [],
                                                "responses": [],
                                            }
                                        ],
                                    }
                                ],
                                "requests": [
                                    {
                                        "id": "28129865-3aa78b71-2c4f-4299-94df-287ed1036409",
                                        "name": "Login",
                                        "method": "POST",
                                        "collection": "28129865-d9f8833b-3dd2-4b07-9634-1831206d5205",
                                        "folder": "28129865-d6dd1092-94d4-462c-be48-4e3cad3b8612",
                                        "responses_order": [],
                                        "responses": [],
                                    }
                                ],
                            }
                        ],
                        "requests": [
                            {
                                "id": "28129865-67c9db4c-d0ed-461c-86d2-9a8c5a5de896",
                                "name": "Example Basic HTTP request",
                                "method": "GET",
                                "collection": "28129865-d9f8833b-3dd2-4b07-9634-1831206d5205",
                                "folder": None,
                                "responses_order": [],
                                "responses": [],
                            }
                        ],
                    }
                ]
            },
        )

    def check(self, module_test, events):
        assert any(
            e.data == "https://www.postman.com/_api/workspace/afa061be-9cb0-4520-9d4d-fe63361daf0f" for e in events
        ), "Failed to detect workspace"
        assert any(
            e.data == "https://www.postman.com/_api/workspace/afa061be-9cb0-4520-9d4d-fe63361daf0f/globals"
            for e in events
        ), "Failed to detect workspace globals"
        assert any(
            e.data == "https://www.postman.com/_api/environment/28129865-fa7edca0-2df6-4187-9805-11845912f567"
            for e in events
        ), "Failed to detect workspace environment"
        assert any(
            e.data == "https://www.postman.com/_api/collection/28129865-d9f8833b-3dd2-4b07-9634-1831206d5205"
            for e in events
        ), "Failed to detect collection"
        assert any(
            e.data == "https://www.postman.com/_api/request/28129865-987c8ac8-bfa9-4bab-ade9-88ccf0597862"
            for e in events
        ), "Failed to detect collection request #1"
        assert any(
            e.data == "https://www.postman.com/_api/request/28129865-3aa78b71-2c4f-4299-94df-287ed1036409"
            for e in events
        ), "Failed to detect collection request #1"
        assert any(
            e.data == "https://www.postman.com/_api/request/28129865-67c9db4c-d0ed-461c-86d2-9a8c5a5de896"
            for e in events
        ), "Failed to detect collection request #1"
