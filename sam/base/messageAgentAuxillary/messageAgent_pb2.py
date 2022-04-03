# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: messageAgent.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='messageAgent.proto',
  package='',
  syntax='proto3',
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_pb=b'\n\x12messageAgent.proto\"\x1d\n\x06Pickle\x12\x13\n\x0bpicklebytes\x18\x01 \x01(\x0c\"\x17\n\x06Status\x12\r\n\x05\x62ooly\x18\x01 \x01(\x08\x32-\n\x0eMessageStorage\x12\x1b\n\x05Store\x12\x07.Pickle\x1a\x07.Status\"\x00\x62\x06proto3'
)




_PICKLE = _descriptor.Descriptor(
  name='Pickle',
  full_name='Pickle',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='picklebytes', full_name='Pickle.picklebytes', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=b"",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=22,
  serialized_end=51,
)


_STATUS = _descriptor.Descriptor(
  name='Status',
  full_name='Status',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='booly', full_name='Status.booly', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=53,
  serialized_end=76,
)

DESCRIPTOR.message_types_by_name['Pickle'] = _PICKLE
DESCRIPTOR.message_types_by_name['Status'] = _STATUS
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

Pickle = _reflection.GeneratedProtocolMessageType('Pickle', (_message.Message,), {
  'DESCRIPTOR' : _PICKLE,
  '__module__' : 'messageAgent_pb2'
  # @@protoc_insertion_point(class_scope:Pickle)
  })
_sym_db.RegisterMessage(Pickle)

Status = _reflection.GeneratedProtocolMessageType('Status', (_message.Message,), {
  'DESCRIPTOR' : _STATUS,
  '__module__' : 'messageAgent_pb2'
  # @@protoc_insertion_point(class_scope:Status)
  })
_sym_db.RegisterMessage(Status)



_MESSAGESTORAGE = _descriptor.ServiceDescriptor(
  name='MessageStorage',
  full_name='MessageStorage',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_start=78,
  serialized_end=123,
  methods=[
  _descriptor.MethodDescriptor(
    name='Store',
    full_name='MessageStorage.Store',
    index=0,
    containing_service=None,
    input_type=_PICKLE,
    output_type=_STATUS,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
])
_sym_db.RegisterServiceDescriptor(_MESSAGESTORAGE)

DESCRIPTOR.services_by_name['MessageStorage'] = _MESSAGESTORAGE

# @@protoc_insertion_point(module_scope)
