from django.contrib import admin

from .models import Articles, Gallery, Reactions, Shares

# Register your models here.

admin.site.register(Articles)
admin.site.register(Reactions)
admin.site.register(Gallery)
admin.site.register(Shares)
