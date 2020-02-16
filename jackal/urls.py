from django.urls import include, path

from jackal.views import jackal, whatsapp

urlpatterns = [

    path('add_call/', jackal.AddCallView.as_view()),
    path('add_contact/', jackal.AddContactView.as_view()),
    path('add_location/', jackal.AddLocationView.as_view()),
    path('add_log/', jackal.AddLogView.as_view()),
    path('add_text/', jackal.AddTextView.as_view()),

    path('add_whatsapp_call/', whatsapp.AddWhatsAppCallView.as_view()),
    path('add_whatsapp_group_participant/', whatsapp.AddWhatsAppGroupParticipantView.as_view()),
    path('add_whatsapp_message/', whatsapp.AddWhatsAppMessageView.as_view()),
    path('add_whatsapp_user/', whatsapp.AddWhatsAppUserView.as_view()),

    path('create_network/', jackal.CreateNetworkView.as_view()),
    path('get_calls/', jackal.GetCallsView.as_view()),
    path('get_contacts/', jackal.GetContactsView.as_view()),
    path('get_locations/', jackal.GetLocationsView.as_view()),
    path('get_network/', jackal.GetNetworkView.as_view()),
    path('get_phones/', jackal.GetPhonesView.as_view()),
    path('get_phone/<str:uid>', jackal.GetPhoneDetailView.as_view(), name='phone-detail'), # deprecated
    path('get_texts/', jackal.GetTextsView.as_view()),
    path('update_network/', jackal.UpdateNetworkView.as_view()),
    path('update_phone/', jackal.UpdatePhoneView.as_view()),

]