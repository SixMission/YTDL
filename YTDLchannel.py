from pytubefix import Channel


version = 0.1


# Create an empty list
video_list = []

print("\nYTDLchannel " + str(version))
print("***************")
print("YouTube Channel Downloader (Exit App with Ctrl + C)\n")

YTchannel = input("YouTube Channel URL: ")

c = Channel(YTchannel)
print(f'\nListing videos by: {c.channel_name}')

i = 0

for video in c.videos:
    i = i+1
    if video.age_restricted == False:
        video_list.append(video.video_id)
        print(str(i) + " - " + str(video.age_restricted) + " - " + video.video_id + " - " + video.title)
    else:
        print(str(i) + " - \033[31m" + str(video.age_restricted) + " - " + video.video_id + " - " + video.title + "\033[0m")


print("Total Videos: " + i + ", NAR videos: " + str(video_list.count))