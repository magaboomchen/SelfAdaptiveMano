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
