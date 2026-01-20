# Generated manually for Phase 3: Skill Plans

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_characterattributes_characterimplant'),
    ]

    operations = [
        migrations.CreateModel(
            name='SkillPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True)),
                ('display_order', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='skill_plans', to='core.user')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='core.skillplan')),
            ],
            options={
                'verbose_name': 'skill plan',
                'verbose_name_plural': 'skill plans',
                'ordering': ['display_order', 'name'],
                'db_table': 'core_skillplan',
            },
        ),
        migrations.CreateModel(
            name='SkillPlanEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('skill_id', models.IntegerField(db_index=True)),
                ('level', models.SmallIntegerField(blank=True, null=True)),
                ('recommended_level', models.SmallIntegerField(blank=True, null=True)),
                ('display_order', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('skill_plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entries', to='core.skillplan')),
            ],
            options={
                'verbose_name': 'skill plan entry',
                'verbose_name_plural': 'skill plan entries',
                'ordering': ['skill_plan', 'display_order'],
                'db_table': 'core_skillplanentry',
            },
        ),
        migrations.AlterUniqueTogether(
            name='skillplanentry',
            unique_together={('skill_plan', 'skill_id')},
        ),
    ]
