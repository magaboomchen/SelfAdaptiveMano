import { axios } from '@/utils/request'

export function getServerSet () {
  return axios({
    url: '/measure/servers/',
    method: 'get'
  })
}

export function getLinks () {
  return axios({
    url: '/measure/links/',
    method: 'get'
  })
}

export function getSwitches () {
  return axios({
    url: '/measure/switches/',
    method: 'get'
  })
}

export function getSFCIs () {
  return axios({
    url: '/measure/sfcis/',
    method: 'get'
  })
}

export function getSFCs () {
  return axios({
    url: '/manager/sfc/',
    method: 'get'
  })
}

export function addSFC (data) {
  return axios({
    url: '/manager/sfc/',
    method: 'post',
    data: data
  })
}

export function delSFC (uuid) {
  return axios({
    url: '/manager/sfc/',
    method: 'delete',
    params: {
      'sfc_uuid': uuid
    }
  })
}
