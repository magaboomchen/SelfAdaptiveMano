<template>
  <div>
    <s-table
      ref="table"
      size="default"
      rowKey="key"
      :columns="columns"
      :data="loadData"
      showPagination="auto"
    >

    </s-table>
  </div>
</template>

<script>
import { getServerSet } from '@/api/monitor'
import { STable } from '@/components'
import { sum } from '@/utils/util'

export default {
  name: 'Server',
  components: {
    STable
  },
  data () {
    return {
      columns: [
        { title: 'ID', dataIndex: 'id' },
        { title: '状态', dataIndex: 'active', customRender: (active) => active ? '正常' : '异常' },
        { title: '类型', dataIndex: 'type' },
        {
          title: 'CPU使用率',
          dataIndex: 'cpu_util',
          customRender: (cpuUtils) => (sum(cpuUtils) / cpuUtils.length).toFixed(2) + '%'
        },
        { title: 'CPU核心数', dataIndex: 'max_cores' },
        { title: '内存页剩余', dataIndex: 'huge_page_free', customRender: pages => sum(pages) },
        { title: '内存页总数', dataIndex: 'huge_page_total', customRender: pages => sum(pages) },
        { title: '内存页大小', dataIndex: 'huge_page_size', customRender: size => size / 1024 + 'MB' },
        { title: '内存总大小', dataIndex: 'max_memory', customRender: text => text + 'GB' }
      ],
      loadData: (pagination, filters, sorter) => {
        return getServerSet().then(res => {
          const start = (pagination.pageNo - 1) * pagination.pageSize
          const end = start + pagination.pageSize
          return {
            'data': res.slice(start, end),
            'pageSize': pagination.pageSize,
            'pageNo': pagination.pageNo,
            'totalPage': Math.ceil(res.length / pagination.pageSize),
            'totalCount': res.length
          }
        })
      }

    }
  },
  created () {
    this.intervalId = setInterval(() => {
      this.$refs.table.refresh(false, false)
    }, 2000)
  },
  destroyed () {
    clearInterval(this.intervalId)
  }
}
</script>

<style scoped>

</style>
