;(function(){

  /**
    * ****************************************************
    *  DOMの構築が完了してから実行する
    * ****************************************************
    */

  $(function() {

    var app = new Vue({
        delimiters: ['${', '}'],
        el: '#spam-result',
        data: {
            probability: '',
            vocabulary: ''
        }
    })

    $("#spam_api_send_button").click(function(){
      const spam_button = $(this)
      spam_button.addClass('disabled');
      mixpanel.track(
          "Played song",
          {"genre": "hip-hop"}
      );
      app.probability = '98%'
      app.vocabulary = '説明会 line 事業 絶対 url 動機 予約 必要 全国 最適 販売 心配 日時 特別 宣伝 アカウント テンプレート 了承'
      /*
      axios.get('http://127.0.0.1:5000/v1/recommend/works/'+workId)
        .then(function (response) {
            # 自動でjsonをjsオブジェクトに変換してくれる
            app.probability = response.data.spam.probability;
            app.vocabulary = response.data.spam.vocabulary;

            spam_button.removeClass('disabled');
        })
        .catch(function (error) {
          alert(error.response.status + '  ' + error.response.data.message);
        });
    */

    });


  });
})();
