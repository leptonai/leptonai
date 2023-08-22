export interface ImagePullSecretMetadata {
  name: string;
}

export interface ImagePullSecretSpec {
  registry_server: string;
  username: string;
  password: string;
  email: string;
}
export interface ImagePullSecret {
  metadata: ImagePullSecretMetadata;
  spec: ImagePullSecretSpec;
}
