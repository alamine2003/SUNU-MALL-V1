from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from apps.users.models import User, Role, UserRole
from .emails import email_de_connexion

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    # Un visiteur ne doit jamais pouvoir s'attribuer un rôle d'administration
    # ou de livraison depuis un payload JSON.
    role_name = serializers.ChoiceField(
        choices=[Role.RoleName.CLIENT, Role.RoleName.MERCHANT],
        write_only=True,
        required=False,
        default=Role.RoleName.CLIENT,
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'phone', 'password', 'role_name')

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Un compte utilise déjà cette adresse email.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        role_name = validated_data.pop('role_name', Role.RoleName.CLIENT)
        
        # Le modèle AbstractUser de Django exige un 'username' par défaut.
        # On peut utiliser l'email comme username pour éviter les erreurs.
        username = validated_data['email']

        user = User.objects.create_user(
            username=username,
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone=validated_data.get('phone', '')
        )
        
        # Attribution du rôle
        role = Role.objects.get(name=role_name)
        UserRole.objects.create(user=user, role=role)
        
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = email_de_connexion(data.get('email', ''))
        password = data.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'), email=email, password=password)
            if not user:
                raise serializers.ValidationError("Identifiants incorrects.", code='authorization')
        else:
            raise serializers.ValidationError("Email et mot de passe requis.", code='authorization')

        if not user.is_active:
            raise serializers.ValidationError("Ce compte est désactivé.", code='authorization')
            
        return user

class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip()


class GuestCheckoutSerializer(serializers.Serializer):
    """
    Crée (ou réutilise) silencieusement un compte client sans mot de passe,
    pour permettre un achat sans étape d'inscription visible avant paiement.
    """
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    phone = serializers.CharField(max_length=30)

    def validate_email(self, value):
        value = value.strip().lower()
        existing = User.objects.filter(email__iexact=value).first()
        if existing:
            raise serializers.ValidationError(
                "Cet email est déjà associé à un compte. Merci de vous connecter."
            )
        return value

    @transaction.atomic
    def save(self):
        data = self.validated_data
        user = User.objects.create_user(
            username=data['email'],
            email=data['email'],
            first_name=data['first_name'],
            last_name=data.get('last_name', ''),
            phone=data['phone'],
        )
        user.set_unusable_password()
        user.save(update_fields=['password'])
        role = Role.objects.get(name=Role.RoleName.CLIENT)
        UserRole.objects.create(user=user, role=role)
        return user


class SetPasswordSerializer(serializers.Serializer):
    """Transforme un compte invité (sans mot de passe) en compte complet."""
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_password(self, value):
        validate_password(value)
        return value
