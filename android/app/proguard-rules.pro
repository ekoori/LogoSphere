# kotlinx.serialization, OkHttp and Coil ship their own R8 rules. Navigation's type-safe routes
# are @Serializable classes looked up by name, so keep their generated serializers.
-keepclassmembers @kotlinx.serialization.Serializable class com.krbavcic.logosphere.** {
    *** Companion;
    kotlinx.serialization.KSerializer serializer(...);
}
-keep,includedescriptorclasses class com.krbavcic.logosphere.**$$serializer { *; }
