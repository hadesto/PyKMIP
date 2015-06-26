# Copyright (c) 2015 The Johns Hopkins University/Applied Physics Laboratory
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging
from testtools import TestCase

from kmip.core.attributes import CryptographicAlgorithm
from kmip.core.attributes import CryptographicLength
from kmip.core.attributes import Name


from kmip.core.enums import AttributeType
from kmip.core.enums import CryptographicAlgorithm as CryptoAlgorithmEnum
from kmip.core.enums import CryptographicUsageMask
from kmip.core.enums import KeyFormatType as KeyFormatTypeEnum
from kmip.core.enums import NameType
from kmip.core.enums import ObjectType
from kmip.core.enums import ResultStatus
from kmip.core.enums import ResultReason
from kmip.core.enums import QueryFunction as QueryFunctionEnum

from kmip.core.factories.attributes import AttributeFactory
from kmip.core.factories.credentials import CredentialFactory
from kmip.core.factories.secrets import SecretFactory

from kmip.core.misc import KeyFormatType

from kmip.core.objects import Attribute
from kmip.core.objects import KeyBlock
from kmip.core.objects import KeyMaterial
from kmip.core.objects import KeyValue
from kmip.core.objects import TemplateAttribute
from kmip.core.objects import PrivateKeyTemplateAttribute
from kmip.core.objects import PublicKeyTemplateAttribute
from kmip.core.objects import CommonTemplateAttribute

from kmip.core.misc import QueryFunction

from kmip.core.secrets import SymmetricKey
from kmip.core.secrets import PrivateKey
from kmip.core.secrets import PublicKey

import pytest


@pytest.mark.usefixtures("client")
class TestIntegration(TestCase):

    def setUp(self):
        super(TestIntegration, self).setUp()

        self.logger = logging.getLogger(__name__)

        self.attr_factory = AttributeFactory()
        self.cred_factory = CredentialFactory()
        self.secret_factory = SecretFactory()

    def tearDown(self):
        super(TestIntegration, self).tearDown()

    def _create_symmetric_key(self, key_name=None):
        """
        Helper function for creating symmetric keys. Used any time a key
        needs to be created.
        :param key_name: name of the key to be created
        :return: returns the result of the "create key" operation as
        provided by the KMIP appliance
        """
        object_type = ObjectType.SYMMETRIC_KEY
        attribute_type = AttributeType.CRYPTOGRAPHIC_ALGORITHM
        algorithm = self.attr_factory.create_attribute(attribute_type,
                                                       CryptoAlgorithmEnum.AES)
        mask_flags = [CryptographicUsageMask.ENCRYPT,
                      CryptographicUsageMask.DECRYPT]
        attribute_type = AttributeType.CRYPTOGRAPHIC_USAGE_MASK
        usage_mask = self.attr_factory.create_attribute(attribute_type,
                                                        mask_flags)
        key_length = 128
        attribute_type = AttributeType.CRYPTOGRAPHIC_LENGTH
        key_length_obj = self.attr_factory.create_attribute(attribute_type,
                                                            key_length)
        name = Attribute.AttributeName('Name')

        if key_name is None:
            key_name = 'Integration Test - Key'

        name_value = Name.NameValue(key_name)

        name_type = Name.NameType(NameType.UNINTERPRETED_TEXT_STRING)
        value = Name(name_value=name_value, name_type=name_type)
        name = Attribute(attribute_name=name, attribute_value=value)
        attributes = [algorithm, usage_mask, key_length_obj, name]
        template_attribute = TemplateAttribute(attributes=attributes)

        return self.client.create(object_type, template_attribute,
                                  credential=None)

    def _create_key_pair(self, key_name=None):
        """
        Helper function for creating private and public keys. Used any time
        a key pair needs to be created.
        :param key_name: name of the key to be created
        :return: returns the result of the "create key" operation as
        provided by the KMIP appliance
        """
        attribute_type = AttributeType.CRYPTOGRAPHIC_ALGORITHM
        algorithm = self.attr_factory.create_attribute(attribute_type,
                                                       CryptoAlgorithmEnum.RSA)
        mask_flags = [CryptographicUsageMask.ENCRYPT,
                      CryptographicUsageMask.DECRYPT]
        attribute_type = AttributeType.CRYPTOGRAPHIC_USAGE_MASK
        usage_mask = self.attr_factory.create_attribute(attribute_type,
                                                        mask_flags)
        key_length = 2048
        attribute_type = AttributeType.CRYPTOGRAPHIC_LENGTH
        key_length_obj = self.attr_factory.create_attribute(attribute_type,
                                                            key_length)
        name = Attribute.AttributeName('Name')

        if key_name is None:
            key_name = 'Integration Test - Key'

        priv_name_value = Name.NameValue(key_name + " Private")
        pub_name_value = Name.NameValue(key_name + " Public")
        name_type = Name.NameType(NameType.UNINTERPRETED_TEXT_STRING)
        priv_value = Name(name_value=priv_name_value, name_type=name_type)
        pub_value = Name(name_value=pub_name_value, name_type=name_type)
        priv_name = Attribute(attribute_name=name, attribute_value=priv_value)
        pub_name = Attribute(attribute_name=name, attribute_value=pub_value)

        common_attributes = [algorithm, usage_mask, key_length_obj]
        private_key_attributes = [priv_name]
        public_key_attributes = [pub_name]

        common = CommonTemplateAttribute(attributes=common_attributes)
        priv_template_attributes = PrivateKeyTemplateAttribute(
            attributes=private_key_attributes)
        pub_template_attributes = PublicKeyTemplateAttribute(
            attributes=public_key_attributes)

        # TODO: Remove trace
        # pytest.set_trace()

        return self.client.\
            create_key_pair(common_template_attribute=common,
                            private_key_template_attribute=
                            priv_template_attributes,
                            public_key_template_attribute=
                            pub_template_attributes)

    def _check_result_status(self, result, result_status_type,
                             result_status_value):
        """
        Helper function for checking the status of KMIP appliance actions.
        Verifies the result status type and value.
        :param result: result object
        :param result_status_type: type of result status received
        :param result_status_value: value of the result status
        """

        result_status = result.result_status.enum
        # Error check the result status type and value
        expected = result_status_type

        self.assertIsInstance(result_status, expected)

        expected = result_status_value

        if result_status is ResultStatus.OPERATION_FAILED:
            self.logger.debug(result)
            self.logger.debug(result.result_reason)
            self.logger.debug(result.result_message)
        self.assertEqual(expected, result_status)

    def _check_uuid(self, uuid, uuid_type):
        """
        Helper function for checking UUID type and value for errors
        :param uuid: UUID of a created key
        :param uuid_type: UUID type
        :return:
        """
        # Error check the UUID type and value
        not_expected = None

        self.assertNotEqual(not_expected, uuid)

        expected = uuid_type
        self.assertEqual(expected, type(uuid))

    def _check_object_type(self, object_type, object_type_type,
                           object_type_value):
        """
        Checks the type and value of a given object type.
        :param object_type:
        :param object_type_type:
        :param object_type_value:
        """
        # Error check the object type type and value
        expected = object_type_type

        self.assertIsInstance(object_type, expected)

        expected = object_type_value

        self.assertEqual(expected, object_type)

    def _check_template_attribute(self, template_attribute,
                                  template_attribute_type, num_attributes,
                                  attribute_features):
        """
        Checks the value and type of a given template attribute
        :param template_attribute:
        :param template_attribute_type:
        :param num_attributes:
        :param attribute_features:
        """
        # Error check the template attribute type
        expected = template_attribute_type

        self.assertIsInstance(template_attribute, expected)

        attributes = template_attribute.attributes

        for i in range(num_attributes):
            features = attribute_features[i]
            self._check_attribute(attributes[i], features[0], features[1],
                                  features[2], features[3])

    def _check_attribute(self, attribute, attribute_name_type,
                         attribute_name_value, attribute_value_type,
                         attribute_value_value):
        """
        Checks the value and type of a given attribute
        :param attribute:
        :param attribute_name_type:
        :param attribute_name_value:
        :param attribute_value_type:
        :param attribute_value_value:
        """
        # Error check the attribute name and value type and value
        attribute_name = attribute.attribute_name
        attribute_value = attribute.attribute_value

        self._check_attribute_name(attribute_name, attribute_name_type,
                                   attribute_name_value)

        if attribute_name_value == 'Unique Identifier':
            self._check_uuid(attribute_value.value, attribute_value_type)
        else:
            self._check_attribute_value(attribute_value, attribute_value_type,
                                        attribute_value_value)

    def _check_attribute_name(self, attribute_name, attribute_name_type,
                              attribute_name_value):
        """
        Checks the attribute name for a given attribute
        :param attribute_name:
        :param attribute_name_type:
        :param attribute_name_value:
        """
        # Error check the attribute name type and value
        expected = attribute_name_type
        observed = type(attribute_name.value)

        self.assertEqual(expected, observed)

        expected = attribute_name_value
        observed = attribute_name.value

        self.assertEqual(expected, observed)

    def _check_attribute_value(self, attribute_value, attribute_value_type,
                               attribute_value_value):
        """
        Checks the attribute value for a given attribute
        :param attribute_value:
        :param attribute_value_type:
        :param attribute_value_value:
        """
        expected = attribute_value_type
        observed = type(attribute_value.value)

        self.assertEqual(expected, observed)

        expected = attribute_value_value
        observed = attribute_value.value

        self.assertEqual(expected, observed)

    def test_discover_versions(self):
        result = self.client.discover_versions()

        expected = ResultStatus.SUCCESS
        observed = result.result_status.enum

        self.assertEqual(expected, observed)

    def test_query(self):
        # Build query function list, asking for all server data.
        query_functions = list()
        query_functions.append(
            QueryFunction(QueryFunctionEnum.QUERY_OPERATIONS))
        query_functions.append(
            QueryFunction(QueryFunctionEnum.QUERY_OBJECTS))
        query_functions.append(
            QueryFunction(QueryFunctionEnum.QUERY_SERVER_INFORMATION))
        query_functions.append(
            QueryFunction(QueryFunctionEnum.QUERY_APPLICATION_NAMESPACES))
        query_functions.append(
            QueryFunction(QueryFunctionEnum.QUERY_EXTENSION_LIST))
        query_functions.append(
            QueryFunction(QueryFunctionEnum.QUERY_EXTENSION_MAP))

        result = self.client.query(query_functions=query_functions)

        expected = ResultStatus.SUCCESS
        observed = result.result_status.enum

        self.assertEqual(expected, observed)

    def test_symmetric_key_create_get_destroy(self):
        """
        Test that symmetric keys are properly created
        """
        key_name = 'Integration Test - Create-Get-Destroy Key'
        result = self._create_symmetric_key(key_name=key_name)

        self._check_result_status(result, ResultStatus, ResultStatus.SUCCESS)
        self._check_object_type(result.object_type.enum, ObjectType,
                                ObjectType.SYMMETRIC_KEY)
        self._check_uuid(result.uuid.value, str)

        result = self.client.get(uuid=result.uuid.value, credential=None)

        self._check_result_status(result, ResultStatus, ResultStatus.SUCCESS)
        self._check_object_type(result.object_type.enum, ObjectType,
                                ObjectType.SYMMETRIC_KEY)
        self._check_uuid(result.uuid.value, str)

        # Check the secret type
        secret = result.secret

        expected = SymmetricKey
        self.assertIsInstance(secret, expected)

        self.logger.debug('Destroying key: ' + key_name + '\n With UUID: ' +
                          result.uuid.value)

        result = self.client.destroy(result.uuid.value)
        self._check_result_status(result, ResultStatus,
                                  ResultStatus.SUCCESS)
        self._check_uuid(result.uuid.value, str)

        # Verify the secret was destroyed
        result = self.client.get(uuid=result.uuid.value, credential=None)

        self._check_result_status(result, ResultStatus,
                                  ResultStatus.OPERATION_FAILED)

        expected = ResultReason
        observed = type(result.result_reason.enum)

        self.assertEqual(expected, observed)

        expected = ResultReason.ITEM_NOT_FOUND
        observed = result.result_reason.enum

        self.assertEqual(expected, observed)

    def test_symmetric_key_register_get_destroy(self):
        """
        Tests that symmetric keys are properly registered
        """
        object_type = ObjectType.SYMMETRIC_KEY
        algorithm_value = CryptoAlgorithmEnum.AES
        mask_flags = [CryptographicUsageMask.ENCRYPT,
                      CryptographicUsageMask.DECRYPT]
        attribute_type = AttributeType.CRYPTOGRAPHIC_USAGE_MASK
        usage_mask = self.attr_factory.create_attribute(attribute_type,
                                                        mask_flags)

        name = Attribute.AttributeName('Name')
        key_name = 'Integration Test - Register-Get-Destroy Key'
        name_value = Name.NameValue(key_name)
        name_type = Name.NameType(NameType.UNINTERPRETED_TEXT_STRING)
        value = Name(name_value=name_value, name_type=name_type)
        name = Attribute(attribute_name=name, attribute_value=value)

        attributes = [usage_mask, name]
        template_attribute = TemplateAttribute(attributes=attributes)

        key_format_type = KeyFormatType(KeyFormatTypeEnum.RAW)

        key_data = (
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00')

        key_material = KeyMaterial(key_data)
        key_value = KeyValue(key_material)
        cryptographic_algorithm = CryptographicAlgorithm(algorithm_value)
        cryptographic_length = CryptographicLength(128)

        key_block = KeyBlock(
            key_format_type=key_format_type,
            key_compression_type=None,
            key_value=key_value,
            cryptographic_algorithm=cryptographic_algorithm,
            cryptographic_length=cryptographic_length,
            key_wrapping_data=None)

        secret = SymmetricKey(key_block)

        result = self.client.register(object_type, template_attribute, secret,
                                      credential=None)

        self._check_result_status(result, ResultStatus, ResultStatus.SUCCESS)
        self._check_uuid(result.uuid.value, str)

        # Check that the returned key bytes match what was provided
        uuid = result.uuid.value
        result = self.client.get(uuid=uuid, credential=None)

        self._check_result_status(result, ResultStatus, ResultStatus.SUCCESS)
        self._check_object_type(result.object_type.enum, ObjectType,
                                ObjectType.SYMMETRIC_KEY)
        self._check_uuid(result.uuid.value, str)

        # Check the secret type
        secret = result.secret

        expected = SymmetricKey

        self.assertIsInstance(secret, expected)

        key_block = result.secret.key_block
        key_value = key_block.key_value
        key_material = key_value.key_material

        expected = key_data
        observed = key_material.value

        self.assertEqual(expected, observed)

        self.logger.debug('Destroying key: ' + key_name + '\nWith UUID: ' +
                          result.uuid.value)

        result = self.client.destroy(result.uuid.value)
        self._check_result_status(result, ResultStatus,
                                  ResultStatus.SUCCESS)
        self._check_uuid(result.uuid.value, str)

        # Verify the secret was destroyed
        result = self.client.get(uuid=uuid, credential=None)

        self._check_result_status(result, ResultStatus,
                                  ResultStatus.OPERATION_FAILED)

        expected = ResultReason
        observed = type(result.result_reason.enum)

        self.assertEqual(expected, observed)

        expected = ResultReason.ITEM_NOT_FOUND
        observed = result.result_reason.enum

        self.assertEqual(expected, observed)

    def test_key_pair_create_get_destroy(self):
        """
        Test that key pairs are properly created
        """
        key_name = 'Integration Test - Create-Get-Destroy Key Pair -'
        result = self._create_key_pair(key_name=key_name)

        # TODO: Remove trace
        # pytest.set_trace()

        self._check_result_status(result, ResultStatus, ResultStatus.SUCCESS)

        # Check UUID value for Private key
        self._check_uuid(result.private_key_uuid.value, str)
        # Check UUID value for Public key
        self._check_uuid(result.public_key_uuid.value, str)

        priv_key_uuid = result.private_key_uuid.value
        pub_key_uuid = result.public_key_uuid.value

        priv_key_result = self.client.get(uuid=priv_key_uuid, credential=None)
        pub_key_result = self.client.get(uuid=pub_key_uuid, credential=None)

        self._check_result_status(priv_key_result, ResultStatus,
                                  ResultStatus.SUCCESS)
        self._check_object_type(priv_key_result.object_type.enum, ObjectType,
                                ObjectType.PRIVATE_KEY)

        # TODO: Remove trace
        # pytest.set_trace()

        self._check_uuid(priv_key_result.uuid.value, str)
        self._check_result_status(pub_key_result, ResultStatus,
                                  ResultStatus.SUCCESS)
        self._check_object_type(pub_key_result.object_type.enum, ObjectType,
                                ObjectType.PUBLIC_KEY)

        self._check_uuid(pub_key_result.uuid.value, str)

        # Check the secret type
        priv_secret = priv_key_result.secret
        pub_secret = pub_key_result.secret

        priv_expected = PrivateKey
        pub_expected = PublicKey

        # TODO: Remove trace
        # pytest.set_trace()

        self.assertIsInstance(priv_secret, priv_expected)
        self.assertIsInstance(pub_secret, pub_expected)

        self.logger.debug('Destroying key: ' + key_name + ' Private' +
                          '\n With UUID: ' + result.private_key_uuid.value)
        destroy_priv_key_result = self.client.destroy(
            result.private_key_uuid.value)

        self._check_result_status(destroy_priv_key_result, ResultStatus,
                                  ResultStatus.SUCCESS)

        self.logger.debug('Destroying key: ' + key_name + ' Public' +
                          '\n With UUID: ' + result.public_key_uuid.value)
        destroy_pub_key_result = self.client.destroy(
            result.public_key_uuid.value)
        self._check_result_status(destroy_pub_key_result, ResultStatus,
                                  ResultStatus.SUCCESS)

        priv_key_uuid = destroy_priv_key_result.uuid.value
        pub_key_uuid = destroy_pub_key_result.uuid.value

        self._check_uuid(priv_key_uuid, str)
        self._check_uuid(pub_key_uuid, str)

        # Verify the secret was destroyed
        priv_key_destroyed_result = self.client.get(uuid=priv_key_uuid)
        pub_key_destroyed_result = self.client.get(uuid=pub_key_uuid)

        self._check_result_status(priv_key_destroyed_result, ResultStatus,
                                  ResultStatus.OPERATION_FAILED)
        self._check_result_status(pub_key_destroyed_result, ResultStatus,
                                  ResultStatus.OPERATION_FAILED)

        expected = ResultReason
        observed_priv = type(priv_key_destroyed_result.result_reason.enum)
        observed_pub = type(pub_key_destroyed_result.result_reason.enum)

        self.assertEqual(expected, observed_priv)
        self.assertEqual(expected, observed_pub)

        expected = ResultReason.ITEM_NOT_FOUND
        observed_priv = priv_key_destroyed_result.result_reason.enum
        observed_pub = pub_key_destroyed_result.result_reason.enum

        self.assertEqual(expected, observed_priv)
        self.assertEqual(expected, observed_pub)

    def test_key_pair_register_get_destroy(self):
        """
        Tests that symmetric keys are properly registered
        """
        priv_key_object_type = ObjectType.PRIVATE_KEY
        pub_key_object_type = ObjectType.PUBLIC_KEY

        mask_flags = [CryptographicUsageMask.ENCRYPT,
                      CryptographicUsageMask.DECRYPT]
        attribute_type = AttributeType.CRYPTOGRAPHIC_USAGE_MASK
        usage_mask = self.attr_factory.create_attribute(attribute_type,
                                                        mask_flags)

        name = Attribute.AttributeName('Name')
        key_name = 'Integration Test - Register-Get-Destroy Key -'

        priv_name_value = Name.NameValue(key_name + " Private")
        pub_name_value = Name.NameValue(key_name + " Public")

        name_type = Name.NameType(NameType.UNINTERPRETED_TEXT_STRING)
        priv_value = Name(name_value=priv_name_value, name_type=name_type)
        pub_value = Name(name_value=pub_name_value, name_type=name_type)

        priv_name = Attribute(attribute_name=name, attribute_value=priv_value)
        pub_name = Attribute(attribute_name=name, attribute_value=pub_value)

        priv_key_attributes = [usage_mask, priv_name]
        pub_key_attributes = [usage_mask, pub_name]

        private_template_attribute = TemplateAttribute(
            attributes=priv_key_attributes)

        public_template_attribute = TemplateAttribute(
            attributes=pub_key_attributes)

        key_format_type = KeyFormatType(KeyFormatTypeEnum.RAW)

        key_data = (
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00')

        key_material = KeyMaterial(key_data)
        key_value = KeyValue(key_material)

        algorithm_value = CryptoAlgorithmEnum.RSA
        cryptographic_algorithm = CryptographicAlgorithm(algorithm_value)
        cryptographic_length = CryptographicLength(2048)

        key_block = KeyBlock(
            key_format_type=key_format_type,
            key_compression_type=None,
            key_value=key_value,
            cryptographic_algorithm=cryptographic_algorithm,
            cryptographic_length=cryptographic_length,
            key_wrapping_data=None)

        priv_secret = PrivateKey(key_block)
        pub_secret = PublicKey(key_block)

        priv_key_result = self.client.register(priv_key_object_type,
                                               private_template_attribute,
                                               priv_secret, credential=None)

        pub_key_result = self.client.register(pub_key_object_type,
                                              public_template_attribute,
                                              pub_secret, credential=None)

        # TODO: Remove trace
        pytest.set_trace()

        self._check_result_status(priv_key_result, ResultStatus,
                                  ResultStatus.SUCCESS)
        self._check_result_status(pub_key_result, ResultStatus,
                                  ResultStatus.SUCCESS)

        self._check_uuid(priv_key_result.uuid.value, str)
        self._check_uuid(pub_key_result.uuid.value, str)

        # Check that the returned key bytes match what was provided
        priv_uuid = priv_key_result.uuid.value
        pub_uuid = pub_key_result.uuid.value

        priv_key_result = self.client.get(uuid=priv_uuid, credential=None)
        pub_key_result = self.client.get(uuid=pub_uuid, credential=None)

        self._check_result_status(priv_key_result, ResultStatus,
                                  ResultStatus.SUCCESS)
        self._check_result_status(pub_key_result, ResultStatus,
                                  ResultStatus.SUCCESS)

        self._check_object_type(priv_key_result.object_type.enum, ObjectType,
                                ObjectType.PRIVATE_KEY)
        self._check_object_type(pub_key_result.object_type.enum, ObjectType,
                                ObjectType.PUBLIC_KEY)

        self._check_uuid(priv_key_result.uuid.value, str)
        self._check_uuid(pub_key_result.uuid.value, str)

        # Check the secret type
        priv_secret = priv_key_result.secret
        pub_secret = pub_key_result.secret

        priv_expected = PrivateKey
        pub_expected = PublicKey

        self.assertIsInstance(priv_secret, priv_expected)
        self.assertIsInstance(pub_secret, pub_expected)

        priv_key_block = priv_key_result.secret.key_block
        priv_key_value = priv_key_block.key_value
        priv_key_material = priv_key_value.key_material

        pub_key_block = pub_key_result.secret.key_block
        pub_key_value = pub_key_block.key_value
        pub_key_material = pub_key_value.key_material

        expected = key_data

        priv_observed = priv_key_material.value
        pub_observed = pub_key_material.value

        self.assertEqual(expected, priv_observed)
        self.assertEqual(expected, pub_observed)

        self.logger.debug('Destroying key: ' + key_name + " Private" +
                          '\nWith " "UUID: ' + priv_key_result.uuid.value)

        priv_result = self.client.destroy(priv_key_result.uuid.value)

        self.logger.debug('Destroying key: ' + key_name + " Private" +
                          '\nWith " "UUID: ' + pub_key_result.uuid.value)
        pub_result = self.client.destroy(pub_key_result.uuid.value)

        self._check_result_status(priv_result, ResultStatus,
                                  ResultStatus.SUCCESS)
        self._check_result_status(pub_result, ResultStatus,
                                  ResultStatus.SUCCESS)

        self._check_uuid(priv_result.uuid.value, str)
        self._check_uuid(pub_result.uuid.value, str)

        # Verify the secret was destroyed
        priv_key_destroyed_result = self.client.get(uuid=priv_uuid,
                                                    credential=None)
        pub_key_destroyed_result = self.client.get(uuid=pub_uuid,
                                                   credential=None)

        self._check_result_status(priv_key_destroyed_result, ResultStatus,
                                  ResultStatus.OPERATION_FAILED)
        self._check_result_status(pub_key_destroyed_result, ResultStatus,
                                  ResultStatus.OPERATION_FAILED)

        expected = ResultReason
        priv_observed = type(priv_key_destroyed_result.result_reason.enum)
        pub_observed = type(pub_key_destroyed_result.result_reason.enum)

        self.assertEqual(expected, priv_observed)
        self.assertEqual(expected, pub_observed)

        expected = ResultReason.ITEM_NOT_FOUND
        priv_observed = priv_key_destroyed_result.result_reason.enum
        pub_observed = pub_key_destroyed_result.result_reason.enum

        self.assertEqual(expected, priv_observed)
        self.assertEqual(expected, pub_observed)
