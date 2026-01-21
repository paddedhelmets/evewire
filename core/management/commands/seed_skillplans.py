"""
Management command to create sample skill plans.

Based on the seed data from the Imperium skill-checker README.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Create sample skill plans for testing'

    def handle(self, *args, **options):
        from core.character.models import SkillPlan, SkillPlanEntry
        from core.eve.models import ItemType

        User = get_user_model()

        # Get or create a test user
        user, created = User.objects.get_or_create(
            username='test_user_seed',
            defaults={
                'eve_character_name': 'Test User',
                'corporation_id': 1,
            }
        )

        if created:
            # Create a test character for this user
            from core.models import Character
            Character.objects.create(
                id=99999999,
                user=user,
                character_name='Test User',
                corporation_id=1,
                corporation_name='Test Corp',
            )
            self.stdout.write(self.style.SUCCESS(f'Created test user: {user.display_name}'))

        # Sample skill plans from skill-checker README
        # These are Imperium-specific plans, we'll create generic versions

        plans_data = [
            {
                'name': 'Basic Industrialist',
                'description': 'Core skills for industry and mining operations',
                'skills': [
                    (3380, 4),  # Industry IV
                    (3386, 3),  # Mining III
                    (25865, 3),  # Mining Frigate III
                    (3403, 3),  # Astrogeology III
                    (22542, 3),  # Mining Barge III
                ],
            },
            {
                'name': 'Basic Combat',
                'description': 'Core skills for combat pilots',
                'skills': [
                    (3300, 3),  # Gunnery III
                    (3301, 3),  # Small Hybrid Turret III
                    (3423, 2),  # Motion Prediction II
                    (3426, 2),  # Sharpshooter II
                    (3327, 2),  # Weapon Upgrades II
                    (3318, 2),  # Mechanics II (for tank)
                ],
            },
            {
                'name': 'Tech II Frigates',
                'description': 'Skills to fly Tech II frigates effectively',
                'skills': [
                    (3327, 5),  # Mechanics V
                    (3392, 5),  # Engineering V
                    (3330, 4),  # Electronics IV
                    (3413, 4),  # Spaceship Command IV
                    (3394, 4),  # Frigate IV
                ],
            },
        ]

        for plan_data in plans_data:
            # Check if plan already exists
            if SkillPlan.objects.filter(owner=user, name=plan_data['name']).exists():
                self.stdout.write(self.style.WARNING(f'Skipping existing plan: {plan_data["name"]}'))
                continue

            # Get display order
            max_order = SkillPlan.objects.filter(
                owner=user,
                parent__isnull=True
            ).first()
            display_order = (max_order.display_order + 1) if max_order else 0

            # Create plan
            plan = SkillPlan.objects.create(
                name=plan_data['name'],
                description=plan_data['description'],
                owner=user,
                display_order=display_order,
            )

            # Add skills
            for i, (skill_id, level) in enumerate(plan_data['skills']):
                # Validate skill exists
                try:
                    ItemType.objects.get(id=skill_id)
                except ItemType.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'Skill {skill_id} not in SDE, skipping'))
                    continue

                SkillPlanEntry.objects.create(
                    skill_plan=plan,
                    skill_id=skill_id,
                    level=level,
                    display_order=i,
                )

            self.stdout.write(self.style.SUCCESS(f'Created plan: {plan.name} with {len(plan_data["skills"])} skills'))

        self.stdout.write(self.style.SUCCESS('Skill plan seeding complete!'))
