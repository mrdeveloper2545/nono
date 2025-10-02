// function pad(num){
//     return num < 10 ? '0' + num : num;
// }

// function updateTime(){
//     const timeElement = document.getElementById('current-time');
//     let[hours,minutes,seconds] = timeElement.textContent.split(':').map(Number);

//     seconds++;
//     if (seconds === 60){
//         seconds = 0;
//         minutes++;
//     }
//     if (minutes === 60){
//         minutes = 0;
//         hours++;
//     }
//     if (hours === 24){
//         hours=0;
//     }

//     timeElement.textContent = '${pad(hours)}:${pad(minutes)}:${pad(seconds)}'
// }

// setInterval(updateTime, 1000);