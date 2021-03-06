import copy

from django.forms import widgets
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.utils import model_meta

from ..core.validators import validate_password


class SetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=128, label=_('Password'),
        style={'widget': widgets.PasswordInput}, validators=[validate_password])


class HyperlinkedModelSerializer(serializers.HyperlinkedModelSerializer):
    """ support for postonly_fields, fields whose value can only be set on post """
    
    def validate(self, attrs):
        """ calls model.clean() """
        attrs = super(HyperlinkedModelSerializer, self).validate(attrs)
        validated_data = dict(attrs)
        ModelClass = self.Meta.model
        # Remove many-to-many relationships from validated_data.
        info = model_meta.get_field_info(ModelClass)
        for field_name, relation_info in info.relations.items():
            if relation_info.to_many and (field_name in validated_data):
                validated_data.pop(field_name)
        if self.instance:
            # on update: Merge provided fields with instance field
            instance = copy.deepcopy(self.instance)
            for key, value in validated_data.items():
                setattr(instance, key, value)
        else:
            instance = ModelClass(**validated_data)
        instance.clean()
        return attrs
    
    def post_only_cleanning(self, instance, validated_data):
        """ removes postonly_fields from attrs """
        model_attrs = dict(**validated_data)
        if instance is not None:
            for attr, value in validated_data.items():
                if attr in self.Meta.postonly_fields:
                    model_attrs.pop(attr)
        return model_attrs
    
    def update(self, instance, validated_data):
        """ removes postonly_fields from attrs when not posting """
        model_attrs = self.post_only_cleanning(instance, validated_data)
        return super(HyperlinkedModelSerializer, self).update(instance, model_attrs)
    
    def partial_update(self, instance, validated_data):
        """ removes postonly_fields from attrs when not posting """
        model_attrs = self.post_only_cleanning(instance, validated_data)
        return super(HyperlinkedModelSerializer, self).partial_update(instance, model_attrs)


class SetPasswordHyperlinkedSerializer(HyperlinkedModelSerializer):
    password = serializers.CharField(max_length=128, label=_('Password'),
        validators=[validate_password], write_only=True, required=False,
        style={'widget': widgets.PasswordInput})
    
    def validate_password(self, attrs, source):
        """ POST only password """
        if self.instance:
            if 'password' in attrs:
                raise serializers.ValidationError(_("Can not set password"))
        elif 'password' not in attrs:
            raise serializers.ValidationError(_("Password required"))
        return attrs
    
    def validate(self, attrs):
        """ remove password in case is not a real model field """
        try:
            self.Meta.model._meta.get_field_by_name('password')
        except models.FieldDoesNotExist:
            pass
        else:
            password = attrs.pop('password', None)
        attrs = super(SetPasswordSerializer, self).validate()
        if password is not None:
            attrs['password'] = password
        return attrs
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        instance = self.Meta.model(**validated_data)
        instance.set_password(password)
        instance.save()
        return instance


#class MultiSelectField(serializers.ChoiceField):
#    widget = widgets.CheckboxSelectMultiple
#    
#    def field_from_native(self, data, files, field_name, into):
#        """ convert multiselect data into comma separated string """
#        if field_name in data:
#            data = data.copy()
#            try:
#                # data is a querydict when using forms
#                data[field_name] = ','.join(data.getlist(field_name))
#            except AttributeError:
#                data[field_name] = ','.join(data[field_name])
#        return super(MultiSelectField, self).field_from_native(data, files, field_name, into)
#    
#    def valid_value(self, value):
#        """ checks for each item if is a valid value """
#        for val in value.split(','):
#            valid = super(MultiSelectField, self).valid_value(val)
#            if not valid:
#                return False
#        return True
