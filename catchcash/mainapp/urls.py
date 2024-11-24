from django.urls import path
from mainapp import views

urlpatterns = [
    path('', views.about, name='about'),
    path('main', views.main, name='main'),
    # path('about', views.about, name='about'),
    path('analysis', views.analysis, name='analysis'),
    path('setting', views.setting, name='setting'),
    path('scope', views.scope, name='scope'),
    path('progression', views.progression, name='progression'),
    path('trophy', views.trophy, name='trophy'),
    path('scope/<int:wallet_id>', views.scope, name='scope'),
    path('goal/<int:wallet_id>', views.mission, name='goal'),
    path('preset/<int:wallet_id>/', views.preset, name='preset'),
        
    path('wallet_detail/<int:id>', views.wallet_detail, name='wallet_detail'),
    
    path('create_wallet/', views.create_wallet, name='create_wallet'),
    path('create_scope/', views.create_scope, name='create_scope'),
    path('create_goal/', views.create_mission, name='create_mission'),
    path('create_preset/', views.create_preset, name='create_preset'),

    path('edit_statement/<int:id>/', views.edit_statement, name='edit_statement'),
    path('delete_statement/<int:id>/', views.delete_statement, name='delete_statement'),
    path('add_statement/', views.add_statement, name='add_statement'),

    path('scope/edit/<int:scope_id>/', views.edit_scope, name='edit_scope'),
    path('scope/delete/<int:scope_id>/', views.delete_scope, name='delete_scope'),

    path('mission/edit/<int:mission_id>/', views.edit_mission, name='edit_mission'),
    path('mission/delete/<int:mission_id>/', views.delete_mission, name='delete_mission'),
    path('missions/donate/<int:mission_id>/', views.donate_to_mission, name='donate_to_mission'),

    path('preset/edit/<int:preset_id>/', views.edit_preset, name='edit_preset'),
    path('preset/delete/<int:preset_id>/', views.delete_preset, name='delete_preset'),
    path('use-preset/<int:preset_id>/', views.use_preset, name='use_preset'),
] 
