#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

__all__ = ('Config', "ConfigGroup")


class BaseConfig:
    '''
    The base config object implements the set and get attribute magic

    Private class
    '''

    def __setattr__(self, name, value):
        super().__setattr__(name, value)

    def __getattribute__(self, name):
        try:
            return super().__getattribute__(name)
        except AttributeError:
            val = ConfigGroup()
            super().__setattr__(name, val)
            return val

    def to_json(self):
        '''
        Wrote this method for testing/demo - will go away
        TODO: Remove and do this in formats/json.py
        '''
        d = {}
        for key, value in self.__dict__.items():
            if isinstance(value, ConfigGroup):
                d[key] = value.to_json()
            else:
                d[key] = value  # Not handling special types right now...this is just a demo

        return d


class Config(BaseConfig):
    '''
    The main config class that the user creates
    '''
    pass


class ConfigGroup(BaseConfig):
    '''
    Class for any sub-fields in the config
    '''
    pass
