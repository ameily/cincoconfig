#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

from xml.etree import ElementTree as ET
from xml.dom import minidom
from typing import Any
from cincoconfig.abc import ConfigFormat, BaseConfig
from cincoconfig.fields import BoolField


class XmlConfigFormat(ConfigFormat):
    '''
    XML configuration file format.

    This class should not be directly referenced. Instead, use the config
    :meth:`~cincoconfig.Config.load` and :meth:`~cincoconfig.Config.save` methods, passing
    *format='xml'*.

    .. code-block:: python

        config.save('filename.xml', format='xml')
        # or
        config.load('filename.xml', format='xml')

    To handle dynamic configurations, the Python type for each XML element is stored in the
    ``type`` attribute.

    .. code-block:: xml

        <x type="int">1024</x>

    When the configuration file is loaded, the formatter will attempt to parse the original Python
    type. If the parsing fails then the original string value is stored in the basic value tree.
    '''

    def __init__(self, root_tag: str = 'config'):
        '''
        :param root_tag: root configuration tag name
        '''
        self.root_tag = root_tag

    def _to_element(self, key: str, value: Any) -> ET.Element:
        '''
        Convert the key/value pair to an XML element.

        :param key: the field key (becomes the tag name)
        :param value: the field valid
        :returns: the element containing the XML encoded key/value pair
        '''
        ele = ET.Element(key)
        if isinstance(value, str):
            ele.attrib['type'] = 'str'
            ele.text = value
        elif isinstance(value, bool):
            ele.attrib['type'] = 'bool'
            ele.text = 'true' if value else 'false'
        elif isinstance(value, int):
            ele.attrib['type'] = 'int'
            ele.text = str(value)
        elif isinstance(value, float):
            ele.attrib['type'] = 'float'
            ele.text = str(value)
        elif value is None:
            ele.attrib['type'] = 'none'
        elif isinstance(value, list):
            ele.attrib['type'] = 'list'
            for item in value:
                sub = self._to_element('item', item)
                ele.append(sub)
        elif isinstance(value, dict):
            ele.attrib['type'] = 'dict'
            for subkey, subval in value.items():
                sub = self._to_element(subkey, subval)
                ele.append(sub)
        else:
            raise TypeError('non-basic type: %s' % str(type(value)))

        return ele

    def _from_element(self, ele: ET.Element, pytype: str = None) -> Any:
        '''
        Parse the XML element to the original Python type. This method will attempt to convert any
        basic types to their original Python type and, if conversion fails, will use the original
        string value. For example:

        .. code-block:: xml

            <x type="int">asdf</x>

        This method will attempt to parse the value, *asdf*, as a :class:`int`, which will fail.
        Then, the method will store the original string value in the basic value tree:

        .. code-block:: python

            tree = {
                'x': 'asdf'
            }

        :param ele: the XML element to convert
        :param pytype: force the Python type attribute rather than reading the Python type from the
            *type* attribute
        :returns: the parsed Python value
        '''
        # pylint: disable=too-many-branches
        pytype = pytype or ele.attrib.get('type')
        text = ele.text or ''
        value = None  # type: Any
        if pytype == 'str':
            value = text
        elif pytype == 'bool':
            if text.lower() in BoolField.TRUE_VALUES:
                value = True
            elif text.lower() in BoolField.FALSE_VALUES:
                value = False
            else:
                value = text
        elif pytype == 'int':
            try:
                value = int(text)
            except:
                value = text
        elif pytype == 'float':
            try:
                value = float(text)
            except:
                value = text
        elif pytype == 'none':
            value = None
        elif pytype == 'list':
            value = []
            for sub in ele:
                item = self._from_element(sub)
                value.append(item)
        elif pytype == 'dict':
            value = {}
            for sub in ele:
                item = self._from_element(sub)
                value[sub.tag] = item
        else:
            value = text

        return value

    def _prettify(self, ele: ET.Element) -> bytes:
        '''
        Pretty print the XML element.

        :param ele: XML element to pretty print
        :returns: the pretty printed XML element
        '''
        rough_string = ET.tostring(ele, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ").encode()

    def dumps(self, config: BaseConfig, tree: dict) -> bytes:
        '''
        Serialize the basic value ``tree`` to an XML :class:`bytes` document. The returned XML
        document will contain a single top-level tag named *root_key* that all other values are
        stored under.

        :param config: current config
        :param tree: basic value tree
        :returns: the serialized basic value tree
        '''
        ele = self._to_element(self.root_tag, tree)
        return self._prettify(ele)

    def loads(self, config: BaseConfig, content: bytes) -> dict:
        '''
        Deserialize the ``content`` (a :class:`bytes` instance containing an XML document) to a
        Python basic value tree. The returned basic value tree will be scoped to *root_tag*, if it
        exists in the deserialized :class:`dict`.

        :param config: current config
        :param content: content to deserialize
        :returns: deserialized basic value tree
        '''
        root = ET.fromstring(content.decode())
        if root.tag != self.root_tag:
            raise ValueError('unexpected root tag: %s' % root.tag)

        return self._from_element(root, 'dict')
