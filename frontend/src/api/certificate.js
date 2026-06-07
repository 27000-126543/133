import request from '@/utils/request'

export function getCertificates(params) {
  return request({
    url: '/certificates/',
    method: 'get',
    params
  })
}

export function getCertificate(certId) {
  return request({
    url: `/certificates/${certId}`,
    method: 'get'
  })
}

export function uploadCertificate(formData, onProgress) {
  return request({
    url: '/certificates/upload',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    onUploadProgress: onProgress
  })
}

export function ocrPreview(formData) {
  return request({
    url: '/certificates/ocr-preview',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

export function verifyCertificate(certId, verified, notes) {
  return request({
    url: `/certificates/${certId}/verify`,
    method: 'post',
    params: { verified, notes }
  })
}

export function getCertificateTypes() {
  return request({
    url: '/certificates/types',
    method: 'get'
  })
}

export function exportCertificates(format = 'excel') {
  return request({
    url: '/certificates/export',
    method: 'get',
    params: { format },
    responseType: 'blob'
  })
}

export function getCertificateImage(certId) {
  return `/api/certificates/image/${certId}`
}
