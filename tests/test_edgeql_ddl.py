#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2016-present MagicStack Inc. and the EdgeDB authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


import unittest  # NOQA

from edb.client import exceptions as client_errors
from edb.server import _testbase as tb


class TestEdgeQLDDL(tb.DDLTestCase):

    async def test_edgeql_ddl_01(self):
        await self.con.execute("""
            CREATE ABSTRACT LINK test::test_link;
        """)

    async def test_edgeql_ddl_02(self):
        await self.con.execute("""
            CREATE ABSTRACT LINK test::test_object_link {
                CREATE PROPERTY test::test_link_prop -> std::int64;
            };

            CREATE TYPE test::TestObjectType {
                CREATE LINK test::test_object_link -> std::Object {
                    CREATE PROPERTY test::test_link_prop -> std::int64 {
                        SET title := 'Test Property';
                    };
                };
            };
        """)

    async def test_edgeql_ddl_03(self):
        await self.con.execute("""
            CREATE ABSTRACT LINK test::test_object_link_prop {
                CREATE PROPERTY test::link_prop1 -> std::str;
            };
        """)

    async def test_edgeql_ddl_04(self):
        await self.con.execute("""
            CREATE TYPE test::A;
            CREATE TYPE test::B EXTENDING test::A;

            CREATE TYPE test::Object1 {
                CREATE REQUIRED LINK test::a -> test::A;
            };

            CREATE TYPE test::Object2 {
                CREATE LINK test::a -> test::B;
            };

            CREATE TYPE test::Object_12
                EXTENDING (test::Object1, test::Object2);
        """)

    async def test_edgeql_ddl_05(self):
        with self.assertRaisesRegex(client_errors.EdgeQLError,
                                    r'cannot create test::my_lower.*func'):

            await self.con.execute("""
                CREATE FUNCTION test::my_lower(s: std::str) -> std::str
                    FROM SQL FUNCTION 'lower';

                CREATE FUNCTION test::my_lower(s: SET OF std::str)
                    -> std::str {
                    SET initial_value := '';
                    FROM SQL FUNCTION 'count';
                };
            """)

        await self.con.execute("""
            DROP FUNCTION test::my_lower(s: std::str);
        """)

        with self.assertRaisesRegex(client_errors.EdgeQLError,
                                    r'cannot create test::my_lower.*func'):

            await self.con.execute("""
                CREATE FUNCTION test::my_lower(s: SET OF anytype)
                    -> std::str {
                    FROM SQL FUNCTION 'count';
                    SET initial_value := '';
                };

                CREATE FUNCTION test::my_lower(s: anytype) -> std::str
                    FROM SQL FUNCTION 'lower';
            """)

        await self.con.execute("""
            DROP FUNCTION test::my_lower(s: anytype);
        """)

    async def test_edgeql_ddl_06(self):
        long_func_name = 'my_sql_func5_' + 'abc' * 50

        await self.con.execute(f"""
            CREATE FUNCTION test::my_sql_func1()
                -> std::str
                FROM SQL $$
                    SELECT 'spam'::text
                $$;

            CREATE FUNCTION test::my_sql_func2(foo: std::str)
                -> std::str
                FROM SQL $$
                    SELECT "foo"::text
                $$;

            CREATE FUNCTION test::my_sql_func4(VARIADIC s: std::str)
                -> std::str
                FROM SQL $$
                    SELECT array_to_string(s, '-')
                $$;

            CREATE FUNCTION test::{long_func_name}()
                -> std::str
                FROM SQL $$
                    SELECT '{long_func_name}'::text
                $$;

            CREATE FUNCTION test::my_sql_func6(a: std::str='a' + 'b')
                -> std::str
                FROM SQL $$
                    SELECT $1 || 'c'
                $$;

            CREATE FUNCTION test::my_sql_func7(s: array<std::int64>)
                -> std::int64
                FROM SQL $$
                    SELECT sum(s)::bigint FROM UNNEST($1) AS s
                $$;
        """)

        await self.assert_query_result(fr"""
            SELECT test::my_sql_func1();
            SELECT test::my_sql_func2('foo');
            SELECT test::my_sql_func4('fizz', 'buzz');
            SELECT test::{long_func_name}();
            SELECT test::my_sql_func6();
            SELECT test::my_sql_func6('xy');
            SELECT test::my_sql_func7([1, 2, 3, 10]);
        """, [
            ['spam'],
            ['foo'],
            ['fizz-buzz'],
            [long_func_name],
            ['abc'],
            ['xyc'],
            [16],
        ])

        await self.con.execute(f"""
            DROP FUNCTION test::my_sql_func1();
            DROP FUNCTION test::my_sql_func2(foo: std::str);
            DROP FUNCTION test::my_sql_func4(VARIADIC s: std::str);
            DROP FUNCTION test::{long_func_name}();
            DROP FUNCTION test::my_sql_func6(a: std::str='a' + 'b');
            DROP FUNCTION test::my_sql_func7(s: array<std::int64>);
        """)

    async def test_edgeql_ddl_07(self):
        with self.assertRaisesRegex(client_errors.EdgeQLError,
                                    r'invalid default value'):
            await self.con.execute(f"""
                CREATE FUNCTION test::broken_sql_func1(
                    a: std::int64=(SELECT schema::ObjectType))
                -> std::str
                FROM SQL $$
                    SELECT 'spam'::text
                $$;
            """)

    async def test_edgeql_ddl_08(self):
        await self.con.execute(f"""
            CREATE FUNCTION test::my_edgeql_func1()
                -> std::str
                FROM EdgeQL $$
                    SELECT 'sp' + 'am'
                $$;

            CREATE FUNCTION test::my_edgeql_func2(s: std::str)
                -> schema::ObjectType
                FROM EdgeQL $$
                    SELECT
                        schema::ObjectType
                    FILTER schema::ObjectType.name = s
                $$;

            CREATE FUNCTION test::my_edgeql_func3(s: std::int64)
                -> std::int64
                FROM EdgeQL $$
                    SELECT s + 10
                $$;

            CREATE FUNCTION test::my_edgeql_func4(i: std::int64)
                -> array<std::int64>
                FROM EdgeQL $$
                    SELECT [i, 1, 2, 3]
                $$;
        """)

        await self.assert_query_result(r"""
            SELECT test::my_edgeql_func1();
            SELECT test::my_edgeql_func2('schema::Object').name;
            SELECT test::my_edgeql_func3(1);
            SELECT test::my_edgeql_func4(42);
        """, [
            ['spam'],
            ['schema::Object'],
            [11],
            [[42, 1, 2, 3]]
        ])

        await self.con.execute(f"""
            DROP FUNCTION test::my_edgeql_func1();
            DROP FUNCTION test::my_edgeql_func2(s: std::str);
            DROP FUNCTION test::my_edgeql_func3(s: std::int64);
            DROP FUNCTION test::my_edgeql_func4(i: std::int64);
        """)

    async def test_edgeql_ddl_09(self):
        await self.con.execute("""
            CREATE FUNCTION test::attr_func_1() -> std::str {
                SET description := 'hello';
                FROM EdgeQL "SELECT '1'";
            };
        """)

        await self.assert_query_result(r"""
            SELECT schema::Function {
                attributes: {
                    @value
                } FILTER .name = 'stdattrs::description'
            } FILTER .name = 'test::attr_func_1';
        """, [
            [{
                'attributes': [{
                    '@value': 'hello'
                }]
            }],
        ])

        await self.con.execute("""
            DROP FUNCTION test::attr_func_1();
        """)

    async def test_edgeql_ddl_10(self):
        await self.con.execute("""
            CREATE FUNCTION test::int_func_1() -> std::int64 {
                FROM EdgeQL "SELECT 1";
            };
        """)

        await self.assert_query_result(r"""
            SELECT test::int_func_1();
        """, [
            [1],
        ])

    async def test_edgeql_ddl_11(self):
        await self.con.execute(r"""
            CREATE TYPE test::TestContainerLinkObjectType {
                CREATE PROPERTY test::test_array_link -> array<std::str>;
                # FIXME: for now dimention specs on the array are
                # disabled pending a syntax change
                # CREATE PROPERTY test::test_array_link_2 ->
                #     array<std::str[10]>;
            };
        """)

    async def test_edgeql_ddl_12(self):
        with self.assertRaisesRegex(
                client_errors.EdgeQLError,
                r"Unexpected '`__subject__`'"):
            await self.con.execute(r"""
                CREATE TYPE test::TestBadContainerLinkObjectType {
                    CREATE PROPERTY test::foo -> std::str {
                        CREATE CONSTRAINT expression
                            ON (`__subject__` = 'foo');
                    };
                };
            """)

    async def test_edgeql_ddl_13(self):
        with self.assertRaisesRegex(
                client_errors.EdgeQLError,
                'reference to a non-existent schema item: self'):
            await self.con.execute(r"""
                CREATE TYPE test::TestBadContainerLinkObjectType {
                    CREATE PROPERTY test::foo -> std::str {
                        CREATE CONSTRAINT expression ON (`self` = 'foo');
                    };
                };
            """)

    @unittest.expectedFailure
    async def test_edgeql_ddl_14(self):
        await self.con.execute("""
            CREATE TYPE test::TestSelfLink1 {
                CREATE PROPERTY test::foo1 -> std::str;
                CREATE PROPERTY test::bar1 -> std::str {
                    SET default := __source__.foo1;
                };
            };
        """)

        await self.assert_query_result(r"""
            INSERT test::TestSelfLink1 {
                foo1 := 'Victor'
            };

            WITH MODULE test
            SELECT TestSelfLink1 {
                foo1,
                bar1,
            };
        """, [
            [1],
            [{'foo1': 'Victor', 'bar1': 'Victor'}]
        ])

    async def test_edgeql_ddl_15(self):
        await self.con.execute(r"""
            CREATE TYPE test::TestSelfLink2 {
                CREATE PROPERTY test::foo2 -> std::str;
                CREATE PROPERTY test::bar2 -> std::str {
                    # NOTE: this is a set of all TestSelfLink2.foo2
                    SET default := test::TestSelfLink2.foo2;
                    SET cardinality := '1*';
                };
            };
        """)

        await self.assert_query_result(r"""
            INSERT test::TestSelfLink2 {
                foo2 := 'Alice'
            };
            INSERT test::TestSelfLink2 {
                foo2 := 'Bob'
            };
            INSERT test::TestSelfLink2 {
                foo2 := 'Carol'
            };

            WITH MODULE test
            SELECT TestSelfLink2 {
                foo2,
                bar2,
            } ORDER BY TestSelfLink2.foo2;
        """, [
            [1],
            [1],
            [1],
            [
                {'bar2': {}, 'foo2': 'Alice'},
                {'bar2': {'Alice'}, 'foo2': 'Bob'},
                {'bar2': {'Alice', 'Bob'}, 'foo2': 'Carol'}
            ],
        ])

    @unittest.expectedFailure
    async def test_edgeql_ddl_16(self):
        # XXX: not sure what the error would say exactly, but
        # cardinality should be an issue here
        with self.assertRaisesRegex(client_errors.EdgeQLError):
            await self.con.execute(r"""
                CREATE TYPE test::TestSelfLink3 {
                    CREATE PROPERTY test::foo3 -> std::str;
                    CREATE PROPERTY test::bar3 -> std::str {
                        # NOTE: this is a set of all TestSelfLink3.foo3
                        SET default := test::TestSelfLink3.foo3;
                    };
                };
            """)

    @unittest.expectedFailure
    async def test_edgeql_ddl_17(self):
        await self.con.execute("""
            CREATE TYPE test::TestSelfLink4 {
                CREATE PROPERTY test::__typename4 -> std::str {
                    SET default := __source__.__type__.name;
                };
            };
        """)

        await self.assert_query_result(r"""
            INSERT test::TestSelfLink4;

            WITH MODULE test
            SELECT TestSelfLink4 {
                __typename4,
            };
        """, [
            [1],
            [{'__typename4': 'test::TestSelfLink4'}]
        ])

    async def test_edgeql_ddl_18(self):
        await self.con.execute("""
            CREATE MODULE foo;
            CREATE MODULE bar;

            SET MODULE foo, b := MODULE bar;

            CREATE SCALAR TYPE foo_t EXTENDING int64 {
                CREATE CONSTRAINT expression ON (__subject__ > 0);
            };

            CREATE SCALAR TYPE b::bar_t EXTENDING int64;

            CREATE TYPE Obj {
                CREATE PROPERTY foo -> foo_t;
                CREATE PROPERTY bar -> b::bar_t;
            };

            CREATE TYPE b::Obj2 {
                CREATE LINK obj -> Obj;
            };
        """)

        await self.assert_query_result(r"""
            WITH MODULE schema
            SELECT ScalarType {
                name,
                constraints: {
                    name
                }
            }
            FILTER .name LIKE '%bar%' OR .name LIKE '%foo%'
            ORDER BY .name;
        """, [
            [
                {'name': 'bar::bar_t', 'constraints': []},
                {'name': 'foo::foo_t', 'constraints': [
                    {'name': 'std::expression'}
                ]},
            ]
        ])

    async def test_edgeql_ddl_19(self):
        await self.con.execute("""
            SET MODULE test;

            CREATE TYPE ActualType {
                CREATE REQUIRED PROPERTY foo -> str;
            };

            CREATE VIEW View1 := ActualType {
                bar := 9
            };

            CREATE VIEW View2 := ActualType {
                connected := (SELECT View1 ORDER BY View1.foo)
            };
        """)

        await self.assert_query_result(r"""
            SET MODULE test;

            INSERT ActualType {
                foo := 'obj1'
            };
            INSERT ActualType {
                foo := 'obj2'
            };

            SELECT View2 {
                foo,
                connected: {
                    foo,
                    bar
                }
            }
            ORDER BY View2.foo;
        """, [
            None,
            [1],
            [1],

            [
                {
                    'foo': 'obj1',
                    'connected': [{
                        'foo': 'obj1',
                        'bar': 9,
                    }, {
                        'foo': 'obj2',
                        'bar': 9,
                    }],
                },
                {
                    'foo': 'obj2',
                    'connected': [{
                        'foo': 'obj1',
                        'bar': 9,
                    }, {
                        'foo': 'obj2',
                        'bar': 9,
                    }],
                }
            ]
        ])

    async def test_edgeql_ddl_20(self):
        with self.assertRaisesRegex(
                client_errors.EdgeQLError,
                r'cannot create test::my_agg.*function:.+anytype.+cannot '
                r'have a non-empty default'):
            await self.con.execute(r"""
                CREATE FUNCTION test::my_agg(
                        s: anytype = [1]) -> array<anytype>
                    FROM SQL FUNCTION "my_agg";
            """)

    async def test_edgeql_ddl_21(self):
        with self.assertRaisesRegex(
                client_errors.SchemaError,
                r'unqualified name and no default module set'):
            await self.con.execute(r"""
                CREATE ABSTRACT ATTRIBUTE test::bad_attr array;
            """)

    async def test_edgeql_ddl_22(self):
        with self.assertRaisesRegex(
                client_errors.SchemaError,
                r'unqualified name and no default module set'):
            await self.con.execute(r"""
                CREATE ABSTRACT ATTRIBUTE test::bad_attr tuple;
            """)

    async def test_edgeql_ddl_23(self):
        with self.assertRaisesRegex(
                client_errors.SchemaError,
                r'unexpected number of subtypes, expecting 1'):
            await self.con.execute(r"""
                CREATE ABSTRACT ATTRIBUTE test::bad_attr
                    array<int64, int64, int64>;
            """)

    async def test_edgeql_ddl_24(self):
        with self.assertRaisesRegex(
                client_errors.SchemaError,
                r'nested arrays are not supported'):
            await self.con.execute(r"""
                CREATE ABSTRACT ATTRIBUTE test::bad_attr array<array<int64>>;
            """)

    async def test_edgeql_ddl_25(self):
        with self.assertRaisesRegex(
                client_errors.SchemaError,
                r'mixing named and unnamed tuple declaration is not '
                r'supported'):
            await self.con.execute(r"""
                CREATE ABSTRACT ATTRIBUTE test::bad_attr
                    tuple<int64, foo:int64>;
            """)

    async def test_edgeql_ddl_26(self):
        with self.assertRaisesRegex(
                client_errors.SchemaError,
                r'unexpected number of subtypes, expecting 1'):
            await self.con.execute(r"""
                CREATE ABSTRACT ATTRIBUTE test::bad_attr array<>;
            """)

    async def test_edgeql_ddl_27(self):
        with self.assertRaisesRegex(
                client_errors.EdgeQLError,
                r'invalid declaration.*unexpected type of the default'):

            await self.con.execute("""
                CREATE FUNCTION test::ddlf_1(s: std::str = 1) -> std::str
                    FROM EdgeQL $$ SELECT "1" $$;
            """)

    async def test_edgeql_ddl_28(self):
        try:
            await self.con.execute("""
                CREATE FUNCTION test::ddlf_2(
                    NAMED ONLY a: int64,
                    NAMED ONLY b: int64
                ) -> std::str
                    FROM EdgeQL $$ SELECT "1" $$;
            """)

            with self.assertRaisesRegex(
                    client_errors.EdgeQLError,
                    r'already defined'):

                await self.con.execute("""
                    CREATE FUNCTION test::ddlf_2(
                        NAMED ONLY b: int64,
                        NAMED ONLY a: int64 = 1
                    ) -> std::str
                        FROM EdgeQL $$ SELECT "1" $$;
                """)

            await self.con.execute("""
                CREATE FUNCTION test::ddlf_2(
                    NAMED ONLY b: str,
                    NAMED ONLY a: int64
                ) -> std::str
                    FROM EdgeQL $$ SELECT "2" $$;
            """)

            await self.assert_query_result(r'''
                SELECT test::ddlf_2(a:=1, b:=1);
                SELECT test::ddlf_2(a:=1, b:='a');
            ''', [
                ['1'],
                ['2'],
            ])

        finally:
            await self.con.execute("""
                DROP FUNCTION test::ddlf_2(
                    NAMED ONLY a: int64,
                    NAMED ONLY b: int64
                );

                DROP FUNCTION test::ddlf_2(
                    NAMED ONLY b: str,
                    NAMED ONLY a: int64
                );
            """)

    @unittest.expectedFailure
    async def test_edgeql_ddl_29(self):
        try:
            await self.con.execute('START TRANSACTION;')

            with self.assertRaises(client_errors.EdgeQLError):
                await self.con.execute("""
                    CREATE FUNCTION test::ddlf_2(
                        a: int64
                    ) -> int64  # should be "decimal", and we want
                                # EdgeDB to complain about that.
                        FROM EdgeQL $$ SELECT sum({a}) $$;
                """)
        finally:
            await self.con.execute('ROLLBACK;')

    async def test_edgeql_ddl_30(self):
        try:
            await self.con.execute('START TRANSACTION;')

            with self.assertRaisesRegex(
                    client_errors.EdgeQLError,
                    r'"\$parameters" cannot not be used in functions'):
                await self.con.execute("""
                    CREATE FUNCTION test::ddlf_3(
                        a: int64
                    ) -> int64
                        FROM EdgeQL $$ SELECT $a $$;
                """)
        finally:
            await self.con.execute('ROLLBACK;')

    async def test_edgeql_ddl_31(self):
        with self.assertRaisesRegex(
                client_errors.EdgeQLError,
                r'parameter `sum` is not callable'):

            await self.con.execute('''
                CREATE FUNCTION test::ddlf_4(
                    sum: int64
                ) -> int64
                    FROM EdgeQL $$
                        SELECT <int64>sum(sum)
                    $$;
            ''')

    async def test_edgeql_ddl_32(self):
        await self.con.execute(r'''
            CREATE FUNCTION test::ddlf_5_1() -> str
                FROM EdgeQL $$
                    SELECT '\u0062'
                $$;

            CREATE FUNCTION test::ddlf_5_2() -> str
                FROM EdgeQL $$
                    SELECT r'\u0062'
                $$;

            CREATE FUNCTION test::ddlf_5_3() -> str
                FROM EdgeQL $$
                    SELECT $a$\u0062$a$
                $$;
        ''')

        try:
            await self.assert_query_result(r'''
                SELECT test::ddlf_5_1();
                SELECT test::ddlf_5_2();
                SELECT test::ddlf_5_3();
            ''', [
                ['b'],
                [r'\u0062'],
                [r'\u0062'],
            ])
        finally:
            await self.con.execute("""
                DROP FUNCTION test::ddlf_5_1();
                DROP FUNCTION test::ddlf_5_2();
                DROP FUNCTION test::ddlf_5_3();
            """)

    async def test_edgeql_ddl_33(self):
        with self.assertRaisesRegex(
                client_errors.EdgeQLError,
                r'cannot create test::ddlf_6\(a: std::int64\) func.*'
                r'function with the same signature is already defined'):

            await self.con.execute(r'''
                CREATE FUNCTION test::ddlf_6(a: int64) -> int64
                    FROM EdgeQL $$ SELECT 11 $$;

                CREATE FUNCTION test::ddlf_6(a: int64) -> float64
                    FROM EdgeQL $$ SELECT 11 $$;
            ''')

        await self.con.execute("""
            DROP FUNCTION test::ddlf_6(a: int64);
        """)

    async def test_edgeql_ddl_34(self):
        with self.assertRaisesRegex(
                client_errors.EdgeQLError,
                r'cannot create test::ddlf_7\(a: SET OF std::int64\) func.*'
                r'SET OF parameters in user-defined EdgeQL functions are '
                r'not yet supported'):

            await self.con.execute(r'''
                CREATE FUNCTION test::ddlf_7(a: SET OF int64) -> int64
                    FROM EdgeQL $$ SELECT 11 $$;
            ''')

        with self.assertRaises(client_errors.SchemaError):
            await self.con.execute("""
                DROP FUNCTION test::ddlf_7(a: SET OF int64);
            """)

    async def test_edgeql_ddl_35(self):
        await self.con.execute(r'''
            CREATE FUNCTION test::ddlf_8(
                    a: int64, NAMED ONLY f: int64) -> int64
                FROM EdgeQL $$ SELECT 11 $$;

            CREATE FUNCTION test::ddlf_8(
                    a: int32, NAMED ONLY f: str) -> int64
                FROM EdgeQL $$ SELECT 12 $$;
        ''')

        try:
            await self.assert_query_result(r'''
                SELECT test::ddlf_8(<int64>10, f := 11);
                SELECT test::ddlf_8(<int32>10, f := '11');
            ''', [
                [11],
                [12],
            ])
        finally:
            await self.con.execute("""
                DROP FUNCTION test::ddlf_8(a: int64, NAMED ONLY f: int64);
                DROP FUNCTION test::ddlf_8(a: int32, NAMED ONLY f: str);
            """)

    async def test_edgeql_ddl_36(self):
        with self.assertRaisesRegex(
                client_errors.EdgeQLError,
                r'cannot create test::ddlf_9.*NAMED ONLY h:.*'
                r'different named only parameters'):

            await self.con.execute(r'''
                CREATE FUNCTION test::ddlf_9(
                        a: int64, NAMED ONLY f: int64) -> int64
                    FROM EdgeQL $$ SELECT 11 $$;

                CREATE FUNCTION test::ddlf_9(
                        a: int32, NAMED ONLY h: str) -> int64
                    FROM EdgeQL $$ SELECT 12 $$;
            ''')

        await self.con.execute("""
            DROP FUNCTION test::ddlf_9(a: int64, NAMED ONLY f: int64);
        """)

    async def test_edgeql_ddl_37(self):
        with self.assertRaisesRegex(
                client_errors.EdgeQLError,
                r'cannot create polymorphic test::ddlf_10.*'
                r'function with different return type'):

            await self.con.execute(r'''
                CREATE FUNCTION test::ddlf_10(
                        a: anytype, b: int64) -> OPTIONAL int64
                    FROM EdgeQL $$ SELECT 11 $$;

                CREATE FUNCTION test::ddlf_10(a: anytype, b: float64) -> str
                    FROM EdgeQL $$ SELECT '12' $$;
            ''')

        await self.con.execute("""
            DROP FUNCTION test::ddlf_10(a: anytype, b: int64);
        """)

    async def test_edgeql_ddl_38(self):
        with self.assertRaisesRegex(
                client_errors.EdgeQLError,
                r'cannot create test::ddlf_11.*'
                r'overloading "FROM SQL FUNCTION"'):

            await self.con.execute(r'''
                CREATE FUNCTION test::ddlf_11(str: std::str) -> int64
                    FROM SQL FUNCTION 'whatever';

                CREATE FUNCTION test::ddlf_11(str: std::int64) -> int64
                    FROM SQL FUNCTION 'whatever2';
            ''')

        await self.con.execute("""
            DROP FUNCTION test::ddlf_11(str: std::str);
        """)

    async def test_edgeql_ddl_39(self):
        with self.assertRaisesRegex(
                client_errors.EdgeQLError,
                r'cannot create test::ddlf_12.*'
                r'function returns a polymorphic type but has no '
                r'polymorphic parameters'):

            await self.con.execute(r'''
                CREATE FUNCTION test::ddlf_12(str: std::str) -> anytype
                    FROM EdgeQL $$ SELECT 1 $$;
            ''')

    async def test_edgeql_ddl_40(self):
        with self.assertRaisesRegex(
                client_errors.SchemaError,
                r'reference to a non-existent schema item: std::anytype'):

            await self.con.execute(r'''
                CREATE FUNCTION test::ddlf_13(f: std::anytype) -> int64
                    FROM EdgeQL $$ SELECT 1 $$;
            ''')

    async def test_edgeql_ddl_41(self):
        with self.assertRaisesRegex(
                client_errors.EdgeQLError,
                r'functions can only contain one statement'):

            await self.con.execute(r'''
                CREATE FUNCTION test::ddlf_14(f: int64) -> int64
                    FROM EdgeQL $$ SELECT 1; SELECT f; $$;
            ''')

    async def test_edgeql_ddl_module_01(self):
        with self.assertRaisesRegex(
                client_errors.SchemaError,
                r"module 'spam' already exists",
                position=20):

            await self.query('''\
                CREATE MODULE spam;
                CREATE MODULE spam;
            ''')

    async def test_edgeql_ddl_operator_01(self):
        await self.query('''
            CREATE INFIX OPERATOR test::`+`
                (left: int64, right: int64) -> int64
                FROM SQL OPERATOR r'+';
        ''')

        await self.assert_query_result('''
            WITH MODULE schema
            SELECT Operator {
                name,
                params: {
                    name,
                    type: {
                        name
                    },
                    typemod
                },
                operator_kind,
                return_typemod
            }
            FILTER
                .name = 'test::+';
        ''', [
            [{
                'name': 'test::+',
                'params': [
                    {
                        'name': 'left',
                        'type': {
                            'name': 'std::int64'
                        },
                        'typemod': 'SINGLETON'
                    },
                    {
                        'name': 'right',
                        'type': {
                            'name': 'std::int64'
                        },
                        'typemod': 'SINGLETON'}
                ],
                'operator_kind': 'INFIX',
                'return_typemod': 'SINGLETON'
            }]
        ])

        await self.query('''
            ALTER INFIX OPERATOR test::`+`
                (left: int64, right: int64)
                SET description := 'my plus';
        ''')

        await self.assert_query_result('''
            WITH MODULE schema
            SELECT Operator {
                name,
                description,
            }
            FILTER
                .name = 'test::+';
        ''', [
            [{
                'name': 'test::+',
                'description': 'my plus',
            }]
        ])

        await self.query("""
            DROP INFIX OPERATOR test::`+` (left: int64, right: int64);
        """)

        await self.assert_query_result('''
            WITH MODULE schema
            SELECT Operator {
                name,
                params: {
                    name,
                    type: {
                        name
                    },
                    typemod
                },
                operator_kind,
                return_typemod
            }
            FILTER
                .name = 'test::+';
        ''', [
            []
        ])

    async def test_edgeql_ddl_operator_02(self):
        try:
            await self.query('''
                CREATE POSTFIX OPERATOR test::`!`
                    (operand: int64) -> int64
                    FROM SQL OPERATOR r'!';

                CREATE PREFIX OPERATOR test::`!`
                    (operand: int64) -> int64
                    FROM SQL OPERATOR r'!!';
            ''')

            await self.assert_query_result('''
                WITH MODULE schema
                SELECT Operator {
                    name,
                    operator_kind,
                }
                FILTER
                    .name = 'test::!'
                ORDER BY
                    .operator_kind;
            ''', [
                [{
                    'name': 'test::!',
                    'operator_kind': 'POSTFIX',
                }, {
                    'name': 'test::!',
                    'operator_kind': 'PREFIX',
                }]
            ])

        finally:
            await self.query('''
                DROP POSTFIX OPERATOR test::`!`
                    (operand: int64);

                DROP PREFIX OPERATOR test::`!`
                    (operand: int64);
            ''')
