import random
from faker import Faker

from core.models import Business, Client

fake = Faker('pt_BR')

# Quantidade de clientes por empresa
CLIENTS_PER_BUSINESS = 10

businesses = Business.objects.filter(active=True)

if not businesses.exists():
    print('❌ Nenhuma empresa encontrada')
    exit()

for business in businesses:
    print(f'🏢 Criando clientes para empresa: {business.name}')

    for _ in range(CLIENTS_PER_BUSINESS):
        Client.objects.create(
            business=business,
            name=fake.name(),
            email=fake.email(),
            phone=fake.phone_number(),
            document=fake.cpf()
        )

print('✅ Clientes fake criados com sucesso')
