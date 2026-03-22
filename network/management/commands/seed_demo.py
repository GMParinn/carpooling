"""
python manage.py seed_demo

Creates a sample road network and demo users for testing.

Demo users:
  admin / admin123        (superuser)
  driver1 / demo1234      (driver)
  driver2 / demo1234      (driver)
  passenger1 / demo1234   (passenger)
  passenger2 / demo1234   (passenger)

Sample network (City Grid):
  Airport ─► Downtown ─► University
     │            │
     ▼            ▼
  Suburb ──► Mall ─► Hospital
                │
                ▼
             Stadium
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from network.models import Node, Edge, ServiceStatus

User = get_user_model()


NODES = [
    {'name': 'Airport',     'latitude': 28.56, 'longitude': 77.10, 'description': 'International Airport'},
    {'name': 'Downtown',    'latitude': 28.63, 'longitude': 77.22, 'description': 'City Centre'},
    {'name': 'University',  'latitude': 28.70, 'longitude': 77.31, 'description': 'Tech University'},
    {'name': 'Suburb',      'latitude': 28.51, 'longitude': 77.18, 'description': 'Residential Area'},
    {'name': 'Mall',        'latitude': 28.58, 'longitude': 77.28, 'description': 'Shopping Mall'},
    {'name': 'Hospital',    'latitude': 28.65, 'longitude': 77.36, 'description': 'City Hospital'},
    {'name': 'Stadium',     'latitude': 28.55, 'longitude': 77.33, 'description': 'Sports Stadium'},
    {'name': 'Park',        'latitude': 28.60, 'longitude': 77.15, 'description': 'Central Park'},
    {'name': 'Station',     'latitude': 28.64, 'longitude': 77.20, 'description': 'Railway Station'},
]

EDGES = [
    ('Airport',    'Downtown'),
    ('Airport',    'Suburb'),
    ('Airport',    'Park'),
    ('Downtown',   'University'),
    ('Downtown',   'Mall'),
    ('Downtown',   'Station'),
    ('University', 'Hospital'),
    ('Suburb',     'Mall'),
    ('Mall',       'Hospital'),
    ('Mall',       'Stadium'),
    ('Park',       'Downtown'),
    ('Park',       'Suburb'),
    ('Station',    'University'),
    ('Station',    'Mall'),
    ('Hospital',   'Stadium'),
    ('Stadium',    'Suburb'),
]

USERS = [
    {'username': 'driver1',     'password': 'demo1234', 'email': 'driver1@demo.com',
     'first_name': 'Arjun',   'last_name': 'Sharma',  'role': 'driver'},
    {'username': 'driver2',     'password': 'demo1234', 'email': 'driver2@demo.com',
     'first_name': 'Priya',   'last_name': 'Mehta',   'role': 'driver'},
    {'username': 'passenger1',  'password': 'demo1234', 'email': 'pass1@demo.com',
     'first_name': 'Rahul',   'last_name': 'Singh',   'role': 'passenger', 'wallet': 100},
    {'username': 'passenger2',  'password': 'demo1234', 'email': 'pass2@demo.com',
     'first_name': 'Sneha',   'last_name': 'Patel',   'role': 'passenger', 'wallet': 50},
]


class Command(BaseCommand):
    help = 'Seeds database with demo data (network + users)'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true', help='Delete all existing data first')

    def handle(self, *args, **options):
        if options['flush']:
            self.stdout.write('Flushing existing data...')
            Edge.objects.all().delete()
            Node.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        # Create superuser
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@demo.com', 'admin123')
            self.stdout.write(self.style.SUCCESS('✓ Created superuser: admin / admin123'))

        # Create nodes
        node_map = {}
        for nd in NODES:
            obj, created = Node.objects.get_or_create(
                name=nd['name'],
                defaults={k: v for k, v in nd.items() if k != 'name'}
            )
            node_map[nd['name']] = obj
            if created:
                self.stdout.write(f'  + Node: {nd["name"]}')

        # Create edges
        for from_name, to_name in EDGES:
            obj, created = Edge.objects.get_or_create(
                from_node=node_map[from_name],
                to_node=node_map[to_name],
            )
            if created:
                self.stdout.write(f'  + Edge: {from_name} → {to_name}')

        # Create users
        for u in USERS:
            if not User.objects.filter(username=u['username']).exists():
                user = User.objects.create_user(
                    username=u['username'],
                    password=u['password'],
                    email=u['email'],
                    first_name=u['first_name'],
                    last_name=u['last_name'],
                    role=u['role'],
                    wallet_balance=u.get('wallet', 0),
                )
                self.stdout.write(self.style.SUCCESS(
                    f'✓ Created {u["role"]}: {u["username"]} / {u["password"]}'
                ))

        # Enable service
        ServiceStatus.objects.get_or_create(id=1, defaults={'enabled': True})

        self.stdout.write(self.style.SUCCESS('\n✅ Demo data seeded successfully!\n'))
        self.stdout.write('  Superuser:   admin / admin123')
        self.stdout.write('  Driver:      driver1 / demo1234')
        self.stdout.write('  Driver:      driver2 / demo1234')
        self.stdout.write('  Passenger:   passenger1 / demo1234  (wallet: $100)')
        self.stdout.write('  Passenger:   passenger2 / demo1234  (wallet: $50)')
