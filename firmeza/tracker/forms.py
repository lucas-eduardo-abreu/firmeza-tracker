from django import forms


class LoginForm(forms.Form):
    username = forms.CharField(label='Usuário', max_length=150)
    password = forms.CharField(label='Senha', widget=forms.PasswordInput)


class SpawnRecordForm(forms.Form):
    death_time = forms.DateTimeField(
        label='Data/Hora da Morte',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        required=False,
    )
