class Docpull < Formula
  include Language::Python::Virtualenv

  desc "One-way sync from Google Docs to Markdown"
  homepage "https://github.com/derek/docpull"
  url "https://github.com/derek/docpull/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "TO_BE_GENERATED"
  license "MIT"

  depends_on "python@3.12"

  resource "cachetools" do
    url "https://files.pythonhosted.org/packages/c3/38/a0f315319737ecf45b4319a8cd1f3a908e29d9277b46942263292115571b/cachetools-5.3.3.tar.gz"
    sha256 "ba29e2dfa0b8b556606f097407ed1aa62080ee108ab0dc5ec9d6a723a007d105"
  end

  resource "google-api-core" do
    url "https://files.pythonhosted.org/packages/b8/b7/481e8a4a272093e95733c15621c7ec75d12e3c0c4a9c3f0b8d1f9f5c9b0c/google-api-core-2.17.1.tar.gz"
    sha256 "9df18a1f87f7c37fcabc54c4049ba70a55ee053d0f0a36ad7e3c1f4e33a0f52e"
  end

  resource "google-api-python-client" do
    url "https://files.pythonhosted.org/packages/d3/ec/0c35d36a67f8c0e8c9c9b8e5e8e8a8f0f5e5f5f5f5f5f5f5f5f5f5f5f5f5/google-api-python-client-2.118.0.tar.gz"
    sha256 "TO_BE_GENERATED"
  end

  resource "google-auth" do
    url "https://files.pythonhosted.org/packages/a2/35/9e1a93d7e5b0d5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e/google-auth-2.28.1.tar.gz"
    sha256 "TO_BE_GENERATED"
  end

  resource "google-auth-httplib2" do
    url "https://files.pythonhosted.org/packages/56/be/217a598a818567b28e859ff087f347475c807a5649296f5f6c5e5e5e5e5e/google-auth-httplib2-0.2.0.tar.gz"
    sha256 "TO_BE_GENERATED"
  end

  resource "google-auth-oauthlib" do
    url "https://files.pythonhosted.org/packages/e5/5e/5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5/google-auth-oauthlib-1.2.0.tar.gz"
    sha256 "TO_BE_GENERATED"
  end

  resource "httplib2" do
    url "https://files.pythonhosted.org/packages/3d/ad/2371116b22d616c194aa5a0b5b44c6e4c1b8fb8b8b8b8b8b8b8b8b8b8b8b/httplib2-0.22.0.tar.gz"
    sha256 "TO_BE_GENERATED"
  end

  resource "pyyaml" do
    url "https://files.pythonhosted.org/packages/cd/e5/af35f7ea75cf72f2cd079c95ee16797de7cd71f29ea7c68ae5ce7be1eda0/PyYAML-6.0.1.tar.gz"
    sha256 "bfdf460b1736c775f2ba9f6a92bca30bc2095067b8a9d77876d1fad6cc3b4a43"
  end

  resource "requests" do
    url "https://files.pythonhosted.org/packages/9d/be/10918a2eac4ae9f02f6cfe6414b7a155ccd8f7f9d4380d62fd5b955065c3/requests-2.31.0.tar.gz"
    sha256 "942c5a758f98d790eaed1a29cb6eefc7ffb0d1cf7af05c3d2791656dbd6ad1e1"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    system "#{bin}/docpull", "--help"
  end
end
